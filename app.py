import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, select, insert, update, delete

from config import Config
from models import (
    metadata,
    users_table,
    skills_table,
    user_skills_table,
    courses_table,
    course_vectors_table,
    user_courses_table,
    user_row_to_dict,
    skill_row_to_dict,
    course_row_to_dict,
)
from errors import register_error_handlers

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.from_object(Config)

# Register external independent error handlers from errors.py
register_error_handlers(app)

# Create database engine using SQLAlchemy Core & PostgreSQL
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])

# Automatically create tables if not existing
metadata.create_all(bind=engine)

# =========================================================
# Automatic Database Seeding on Startup
# =========================================================
def auto_seed_database():
    with engine.begin() as conn:
        existing_courses = conn.execute(select(courses_table)).all()
        if len(existing_courses) == 0:
            skills_data = [
                ("Python", "Programming language for AI and backend"),
                ("SQL", "Database query language"),
                ("Machine Learning", "AI algorithms and data modeling"),
                ("Data Analysis", "Exploratory data analysis and visualization"),
                ("Flask", "Python Web Framework"),
                ("PostgreSQL", "Relational Database Management System"),
                ("Docker", "Containerization platform"),
                ("Git", "Version control system"),
            ]
            for name, desc in skills_data:
                conn.execute(
                    insert(skills_table).values(
                        name=name,
                        description=desc,
                        is_deleted=False,
                        deleted_at=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

            courses_data = [
                ("AI Data Science Bootcamp", "Master AI, Data Analysis, and Python from scratch with real-world projects.", "Dr. Sarah Ali", "Python, SQL, Data Analysis"),
                ("Advanced Web Systems with Flask", "Build high-performance REST APIs and scalable architectures.", "Eng. Khaled Omar", "Python, Flask, SQL"),
                ("Deep Learning & NLP Mastery", "Neural networks and Large Language Models using modern Python stacks.", "Dr. Tareq Hassan", "Python, Machine Learning"),
                ("Enterprise PostgreSQL Design", "Database schemas, migrations, indexing, and vector similarity.", "Eng. Laila Mansour", "SQL, PostgreSQL"),
                ("DevOps & Docker Deployment", "Deploy scalable Flask applications and PostgreSQL containers in production.", "Eng. Tariq Mansour", "Docker, Git, Python"),
            ]
            for title, desc, inst, reqs in courses_data:
                res = conn.execute(
                    insert(courses_table).values(
                        title=title,
                        description=desc,
                        instructor=inst,
                        skill_requirements=reqs,
                        is_deleted=False,
                        deleted_at=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                c_id = res.inserted_primary_key[0] if res.inserted_primary_key else None
                if c_id:
                    conn.execute(
                        insert(course_vectors_table).values(
                            course_id=c_id,
                            embedding_vector="[0.12, 0.45, 0.88, 0.33]",
                            is_deleted=False,
                            deleted_at=None,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                    )

auto_seed_database()

# =========================================================
# JWT Authentication Helper
# =========================================================
def generate_jwt_token(user_row):
    payload = {
        "sub": user_row["id"],
        "username": user_row["username"],
        "email": user_row["email"],
        "exp": datetime.utcnow() + timedelta(seconds=app.config["JWT_ACCESS_TOKEN_EXPIRES"]),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, app.config["JWT_SECRET_KEY"], algorithm="HS256")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized", "message": "Missing Bearer Token"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
            user_id = payload.get("sub")
            with engine.connect() as conn:
                user_row = conn.execute(
                    select(users_table).where(
                        (users_table.c.id == user_id) &
                        ((users_table.c.is_deleted == False) | (users_table.c.is_deleted == None))
                    )
                ).mappings().first()
                if not user_row:
                    return jsonify({"error": "Unauthorized", "message": "User not found or deleted"}), 401
                g.current_user = user_row
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Unauthorized", "message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Unauthorized", "message": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated

# =========================================================
# Static HTML5 Frontend Routes (100% Static - No Jinja)
# =========================================================
@app.route("/")
def index():
    return send_from_directory("templates", "courses.html")

@app.route("/login")
def login_page():
    return send_from_directory("templates", "login.html")

@app.route("/register")
def register_page():
    return send_from_directory("templates", "register.html")

@app.route("/courses")
def courses_page():
    return send_from_directory("templates", "courses.html")

@app.route("/course-details")
def course_details_page():
    return send_from_directory("templates", "course-details.html")

@app.route("/recommendations")
def recommendations_page():
    return send_from_directory("templates", "recommendations.html")

@app.route("/profile")
def profile_page():
    return send_from_directory("templates", "profile.html")

# =========================================================
# Authentication & Registration Routes (/api/auth)
# =========================================================
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not email or not password:
        return jsonify({"error": "Bad Request", "message": "Username, email and password are required"}), 400
        
    with engine.begin() as conn:
        existing_email = conn.execute(
            select(users_table).where(users_table.c.email == email)
        ).first()
        if existing_email:
            return jsonify({"error": "Bad Request", "message": "Email is already registered"}), 400
            
        existing_username = conn.execute(
            select(users_table).where(users_table.c.username == username)
        ).first()
        if existing_username:
            return jsonify({"error": "Bad Request", "message": "Username is already taken"}), 400

        hashed_password = generate_password_hash(password)
        
        insert_user_stmt = insert(users_table).values(
            username=username,
            email=email,
            password=hashed_password,
            phone=data.get("phone", ""),
            age=int(data.get("age", 0)) if data.get("age") else None,
            major=data.get("major", ""),
            is_deleted=False,
            deleted_at=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        res = conn.execute(insert_user_stmt)
        user_id = res.inserted_primary_key[0] if res.inserted_primary_key else None
        
        new_user = conn.execute(
            select(users_table).where(users_table.c.id == user_id)
        ).mappings().first()

        skills_list = data.get("skills", [])
        for skill_item in skills_list:
            skill_name = skill_item.get("name") if isinstance(skill_item, dict) else str(skill_item)
            proficiency = skill_item.get("proficiency", "intermediate") if isinstance(skill_item, dict) else "intermediate"
            
            skill_row = conn.execute(
                select(skills_table).where(
                    (skills_table.c.name == skill_name) &
                    ((skills_table.c.is_deleted == False) | (skills_table.c.is_deleted == None))
                )
            ).mappings().first()
            
            if skill_row:
                conn.execute(
                    insert(user_skills_table).values(
                        user_id=new_user["id"],
                        skill_id=skill_row["id"],
                        proficiency_level=proficiency,
                        is_deleted=False,
                        deleted_at=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

    token = generate_jwt_token(new_user)
    return jsonify({
        "user": {
            "id": new_user["id"],
            "username": new_user["username"],
            "email": new_user["email"]
        },
        "token": token
    }), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Bad Request", "message": "Email and password are required"}), 400

    with engine.connect() as conn:
        user = conn.execute(
            select(users_table).where(
                (users_table.c.email == email) &
                ((users_table.c.is_deleted == False) | (users_table.c.is_deleted == None))
            )
        ).mappings().first()
        
        if not user or not check_password_hash(user["password"], password):
            return jsonify({"error": "Unauthorized", "message": "Invalid email or password"}), 401

    token = generate_jwt_token(user)
    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        },
        "token": token
    }), 200

# =========================================================
# User Profile, Name Editing & Soft Deletion (/api/users)
# =========================================================
@app.route("/api/users/me", methods=["GET"])
@token_required
def get_current_user_profile():
    user = g.current_user
    with engine.connect() as conn:
        stmt_skills = (
            select(
                user_skills_table.c.id,
                user_skills_table.c.user_id,
                user_skills_table.c.skill_id,
                skills_table.c.name.label("skill_name"),
                user_skills_table.c.proficiency_level
            )
            .select_from(
                user_skills_table.join(skills_table, user_skills_table.c.skill_id == skills_table.c.id)
            )
            .where(
                (user_skills_table.c.user_id == user["id"]) &
                ((user_skills_table.c.is_deleted == False) | (user_skills_table.c.is_deleted == None))
            )
        )
        skills_rows = conn.execute(stmt_skills).mappings().all()

        stmt_courses = (
            select(
                user_courses_table.c.id.label("enrollment_id"),
                courses_table.c.id.label("course_id"),
                courses_table.c.title,
                courses_table.c.instructor,
                courses_table.c.description,
                user_courses_table.c.enrolled_at
            )
            .select_from(
                user_courses_table.join(courses_table, user_courses_table.c.course_id == courses_table.c.id)
            )
            .where(
                (user_courses_table.c.user_id == user["id"]) &
                ((user_courses_table.c.is_deleted == False) | (user_courses_table.c.is_deleted == None))
            )
        )
        enrolled_rows = conn.execute(stmt_courses).mappings().all()

    return jsonify({
        "user": user_row_to_dict(user),
        "skills": [dict(r) for r in skills_rows],
        "enrolled_courses": [dict(r) for r in enrolled_rows]
    }), 200

@app.route("/api/users/me", methods=["PUT"])
@token_required
def update_user_profile():
    data = request.get_json(force=True, silent=True) or {}
    new_username = data.get("username", "").strip()
    phone = data.get("phone", "").strip()
    major = data.get("major", "").strip()
    age = int(data.get("age", 0)) if data.get("age") else None

    if not new_username:
        return jsonify({"error": "Bad Request", "message": "Username is required"}), 400

    with engine.begin() as conn:
        existing = conn.execute(
            select(users_table).where(
                (users_table.c.username == new_username) &
                (users_table.c.id != g.current_user["id"]) &
                ((users_table.c.is_deleted == False) | (users_table.c.is_deleted == None))
            )
        ).first()

        if existing:
            return jsonify({
                "error": "Bad Request",
                "message": "This username is already taken by another student. Please choose a different username."
            }), 400

        conn.execute(
            update(users_table)
            .where(users_table.c.id == g.current_user["id"])
            .values(
                username=new_username,
                phone=phone,
                major=major,
                age=age,
                updated_at=datetime.utcnow()
            )
        )

        updated_user = conn.execute(
            select(users_table).where(users_table.c.id == g.current_user["id"])
        ).mappings().first()

    return jsonify({
        "message": "Profile details updated successfully",
        "user": user_row_to_dict(updated_user)
    }), 200

@app.route("/api/users/me/skills", methods=["POST"])
@token_required
def add_user_skill():
    data = request.get_json(force=True, silent=True) or {}
    skill_name = data.get("name", "").strip()
    proficiency = data.get("proficiency", "intermediate")

    if not skill_name:
        return jsonify({"error": "Bad Request", "message": "Skill name is required"}), 400

    with engine.begin() as conn:
        skill_row = conn.execute(
            select(skills_table).where(
                (skills_table.c.name == skill_name) &
                ((skills_table.c.is_deleted == False) | (skills_table.c.is_deleted == None))
            )
        ).mappings().first()
        
        if not skill_row:
            return jsonify({
                "error": "Bad Request", 
                "message": "Cannot add a non-existent skill. Please select an available skill from the platform list."
            }), 400
            
        skill_id = skill_row["id"]

        existing = conn.execute(
            select(user_skills_table).where(
                (user_skills_table.c.user_id == g.current_user["id"]) &
                (user_skills_table.c.skill_id == skill_id)
            )
        ).first()

        if existing:
            conn.execute(
                update(user_skills_table)
                .where(
                    (user_skills_table.c.user_id == g.current_user["id"]) &
                    (user_skills_table.c.skill_id == skill_id)
                )
                .values(
                    proficiency_level=proficiency, 
                    is_deleted=False, 
                    deleted_at=None,
                    updated_at=datetime.utcnow()
                )
            )
        else:
            conn.execute(
                insert(user_skills_table).values(
                    user_id=g.current_user["id"],
                    skill_id=skill_id,
                    proficiency_level=proficiency,
                    is_deleted=False,
                    deleted_at=None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )

    return jsonify({"message": "Skill added successfully"}), 200

@app.route("/api/users/me/skills/<int:skill_id>", methods=["DELETE"])
@token_required
def soft_delete_user_skill(skill_id):
    with engine.begin() as conn:
        conn.execute(
            update(user_skills_table)
            .where(
                (user_skills_table.c.user_id == g.current_user["id"]) &
                (user_skills_table.c.skill_id == skill_id)
            )
            .values(is_deleted=True, deleted_at=datetime.utcnow())
        )
    return jsonify({"message": "Skill removed from your profile successfully"}), 200

@app.route("/api/users/me/courses/<int:course_id>", methods=["DELETE"])
@token_required
def soft_delete_user_course(course_id):
    with engine.begin() as conn:
        conn.execute(
            update(user_courses_table)
            .where(
                (user_courses_table.c.user_id == g.current_user["id"]) &
                (user_courses_table.c.course_id == course_id)
            )
            .values(is_deleted=True, deleted_at=datetime.utcnow())
        )
    return jsonify({"message": "Course enrollment removed successfully"}), 200

# =========================================================
# Course Enrollment Route (/api/courses/<id>/enroll)
# =========================================================
@app.route("/api/courses/<int:course_id>/enroll", methods=["POST"])
@token_required
def enroll_in_course(course_id):
    with engine.begin() as conn:
        course = conn.execute(
            select(courses_table).where(
                (courses_table.c.id == course_id) &
                ((courses_table.c.is_deleted == False) | (courses_table.c.is_deleted == None))
            )
        ).first()
        if not course:
            return jsonify({"error": "Not Found", "message": "Course not found"}), 404

        existing = conn.execute(
            select(user_courses_table).where(
                (user_courses_table.c.user_id == g.current_user["id"]) &
                (user_courses_table.c.course_id == course_id)
            )
        ).mappings().first()

        if existing:
            if existing["is_deleted"]:
                conn.execute(
                    update(user_courses_table)
                    .where(
                        (user_courses_table.c.user_id == g.current_user["id"]) &
                        (user_courses_table.c.course_id == course_id)
                    )
                    .values(is_deleted=False, deleted_at=None, enrolled_at=datetime.utcnow())
                )
                return jsonify({"message": "Successfully re-enrolled in course!"}), 201
            return jsonify({"message": "You are already enrolled in this course!"}), 200

        conn.execute(
            insert(user_courses_table).values(
                user_id=g.current_user["id"],
                course_id=course_id,
                is_deleted=False,
                deleted_at=None,
                enrolled_at=datetime.utcnow()
            )
        )

    return jsonify({"message": "Successfully enrolled in course!"}), 201

# =========================================================
# Course Catalog & Recommendations (/api/courses)
# =========================================================
@app.route("/api/courses", methods=["GET"])
def list_courses():
    search = request.args.get("search", "").lower()
    with engine.connect() as conn:
        rows = conn.execute(
            select(courses_table).where(
                (courses_table.c.is_deleted == False) | (courses_table.c.is_deleted == None)
            )
        ).mappings().all()
        
    result = []
    for row in rows:
        data = course_row_to_dict(row)
        if search and search not in data["title"].lower() and search not in data["description"].lower():
            continue
        result.append(data)
    return jsonify({"courses": result}), 200

@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course_details(course_id):
    with engine.connect() as conn:
        row = conn.execute(
            select(courses_table).where(
                (courses_table.c.id == course_id) &
                ((courses_table.c.is_deleted == False) | (courses_table.c.is_deleted == None))
            )
        ).mappings().first()
        
    if not row:
        return jsonify({"error": "Not Found", "message": "Course not found"}), 404
    return jsonify({"course": course_row_to_dict(row)}), 200

@app.route("/api/recommendations", methods=["GET"])
@token_required
def get_recommendations():
    user = g.current_user
    with engine.connect() as conn:
        stmt = (
            select(skills_table.c.name)
            .select_from(user_skills_table.join(skills_table, user_skills_table.c.skill_id == skills_table.c.id))
            .where(
                (user_skills_table.c.user_id == user["id"]) &
                ((user_skills_table.c.is_deleted == False) | (user_skills_table.c.is_deleted == None))
            )
        )
        user_skills_rows = conn.execute(stmt).all()
        user_skill_names = set(r[0].lower() for r in user_skills_rows if r[0])

        courses_rows = conn.execute(
            select(courses_table).where(
                (courses_table.c.is_deleted == False) | (courses_table.c.is_deleted == None)
            )
        ).mappings().all()

    recommendations = []
    for row in courses_rows:
        c_dict = course_row_to_dict(row)
        reqs = [r.lower() for r in c_dict["skill_requirements"] if r]
        if not reqs:
            match_score = 50
            matched_skills = []
        else:
            matched_skills = [r for r in reqs if r in user_skill_names]
            match_score = int((len(matched_skills) / len(reqs)) * 100) if reqs else 0
            if match_score == 0 and len(user_skill_names) > 0:
                match_score = 25

        c_dict["match_score"] = match_score
        c_dict["matched_skills"] = matched_skills
        recommendations.append(c_dict)

    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    return jsonify({"recommendations": recommendations}), 200

@app.route("/api/skills", methods=["GET"])
def get_all_skills():
    with engine.connect() as conn:
        rows = conn.execute(
            select(skills_table).where(
                (skills_table.c.is_deleted == False) | (skills_table.c.is_deleted == None)
            )
        ).mappings().all()
    return jsonify({"skills": [skill_row_to_dict(r) for r in rows]}), 200

@app.route("/api/seed", methods=["POST"])
def seed_database():
    with engine.begin() as conn:
        existing_courses = conn.execute(select(courses_table)).all()
        if len(existing_courses) == 0:
            skills_data = [
                ("Python", "Programming language for AI and backend"),
                ("SQL", "Database query language"),
                ("Machine Learning", "AI algorithms and data modeling"),
                ("Data Analysis", "Exploratory data analysis and visualization"),
                ("Flask", "Python Web Framework"),
                ("PostgreSQL", "Relational Database Management System"),
                ("Docker", "Containerization platform"),
                ("Git", "Version control system"),
            ]
            for name, desc in skills_data:
                conn.execute(
                    insert(skills_table).values(
                        name=name,
                        description=desc,
                        is_deleted=False,
                        deleted_at=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

            courses_data = [
                ("AI Data Science Bootcamp", "Master AI, Data Analysis, and Python from scratch with real-world projects.", "Dr. Sarah Ali", "Python, SQL, Data Analysis"),
                ("Advanced Web Systems with Flask", "Build high-performance REST APIs and scalable architectures.", "Eng. Khaled Omar", "Python, Flask, SQL"),
                ("Deep Learning & NLP Mastery", "Neural networks and Large Language Models using modern Python stacks.", "Dr. Tareq Hassan", "Python, Machine Learning"),
                ("Enterprise PostgreSQL Design", "Database schemas, migrations, indexing, and vector similarity.", "Eng. Laila Mansour", "SQL, PostgreSQL"),
                ("DevOps & Docker Deployment", "Deploy scalable Flask applications and PostgreSQL containers in production.", "Eng. Tariq Mansour", "Docker, Git, Python"),
            ]
            for title, desc, inst, reqs in courses_data:
                res = conn.execute(
                    insert(courses_table).values(
                        title=title,
                        description=desc,
                        instructor=inst,
                        skill_requirements=reqs,
                        is_deleted=False,
                        deleted_at=None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                c_id = res.inserted_primary_key[0] if res.inserted_primary_key else None
                if c_id:
                    conn.execute(
                        insert(course_vectors_table).values(
                            course_id=c_id,
                            embedding_vector="[0.12, 0.45, 0.88, 0.33]",
                            is_deleted=False,
                            deleted_at=None,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                    )

            return jsonify({"message": "Database seeded successfully"}), 201
    return jsonify({"message": "Database already seeded"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
