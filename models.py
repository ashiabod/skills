from datetime import datetime
from sqlalchemy import (
    MetaData, Table, Column, Integer, String, Text, ForeignKey, DateTime
)


metadata = MetaData()

users_table = Table(
    'users',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('username', String(80), unique=True, nullable=False),
    Column('email', String(120), unique=True, nullable=False),
    Column('password', String(255), nullable=False),
    Column('phone', String(20), nullable=True),
    Column('age', Integer, nullable=True),
    Column('major', String(100), nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

skills_table = Table(
    'skills',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(100), unique=True, nullable=False),
    Column('description', Text, nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

user_skills_table = Table(
    'user_skills',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('skill_id', Integer, ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
    Column('proficiency_level', String(50), default="beginner"),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

courses_table = Table(
    'courses',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('title', String(200), nullable=False),
    Column('description', Text, nullable=True),
    Column('instructor', String(100), nullable=True),
    Column('skill_requirements', Text, nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

course_vectors_table = Table(
    'course_vectors',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('course_id', Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
    Column('embedding_vector', Text, nullable=True),
    Column('created_at', DateTime, default=datetime.utcnow),
    Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)

# جدول تسجيل الطلاب في الدورات التدريبية (User Courses Enrollment)
user_courses_table = Table(
    'user_courses',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('course_id', Integer, ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
    Column('enrolled_at', DateTime, default=datetime.utcnow),
)

def user_row_to_dict(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "phone": row["phone"],
        "age": row["age"],
        "major": row["major"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None
    }

def skill_row_to_dict(row):
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"]
    }

def course_row_to_dict(row):
    if not row:
        return None
    reqs = [s.strip() for s in row["skill_requirements"].split(",")] if row.get("skill_requirements") else []
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "instructor": row["instructor"],
        "skill_requirements": reqs
    }
