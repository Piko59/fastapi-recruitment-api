from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Optional
import oracledb
import upstash_redis as redis
from datetime import datetime

app = FastAPI()

# Upstash Redis configuration
redis_client = redis.Redis(url="https://fine-hamster-32812.upstash.io", token="your-token-key")

# Oracle DB configuration(EDIT THIS AREA!!!)
dsn = oracledb.makedsn("oracle-xe", 1521, sid="XE")
connection = oracledb.connect(user="YourUsername", password="YourPassword", dsn=dsn)

# Pydantic models
class User(BaseModel):
    username: str
    password: str
    role: str

class Job(BaseModel):
    title: str
    description: Optional[str] = None
    department: Optional[str] = None

class Interview(BaseModel):
    user_id: int
    job_id: int
    interview_date: str
    interview_result: Optional[str] = "Pending"

class Application(BaseModel):
    user_id: int
    job_id: int
    status: Optional[str] = "Applied"

# Abstract Base Class
class BaseUser:
    def __init__(self, user_id: int, username: str, role: str):
        self.user_id = user_id
        self.username = username
        self.role = role

    def can_create_job(self) -> bool:
        return False

    def can_review_applications(self) -> bool:
        return False

    def can_apply_for_job(self) -> bool:
        return False

    def can_delete(self) -> bool:
        return False

    def can_update(self) -> bool:
        return False

    def can_manage_users(self) -> bool:
        return False

# Inherited Classes
class Admin(BaseUser):
    def __init__(self, user_id: int, username: str):
        super().__init__(user_id, username, "Admin")

    def can_create_job(self) -> bool:
        return True

    def can_review_applications(self) -> bool:
        return True

    def can_apply_for_job(self) -> bool:
        return True

    def can_delete(self) -> bool:
        return True

    def can_update(self) -> bool:
        return True

    def can_manage_users(self) -> bool:
        return True

class Recruiter(BaseUser):
    def __init__(self, user_id: int, username: str):
        super().__init__(user_id, username, "Recruiter")

    def can_create_job(self) -> bool:
        return True

    def can_review_applications(self) -> bool:
        return True

    def can_update(self) -> bool:
        return True

class Candidate(BaseUser):
    def __init__(self, user_id: int, username: str):
        super().__init__(user_id, username, "Candidate")

    def can_apply_for_job(self) -> bool:
        return True

# Dependency to get current user
def get_current_user(request: Request, token: str):
    user_id = redis_client.get(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    cursor = connection.cursor()
    cursor.execute("SELECT USER_ID, USERNAME, ROLE FROM USERACCOUNTS WHERE USER_ID = :1", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    request.state.user_id = user[0]  # Kullanıcı kimliğini request.state'e ekleyin
    if user[2] == "Admin":
        return Admin(user[0], user[1])
    elif user[2] == "Recruiter":
        return Recruiter(user[0], user[1])
    elif user[2] == "Candidate":
        return Candidate(user[0], user[1])
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")

# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        # Kullanıcı kimliğini veya IP adresini al
        user_id = request.state.user_id if hasattr(request.state, "user_id") else request.client.host
        
        # Rate limit anahtarını oluştur (kullanıcı bazlı)
        key = f"rate_limit:{user_id}"
        print(f"Rate limit key: {key}")
        
        # Mevcut istek sayısını al
        current_count = redis_client.get(key)
        print(f"Current count: {current_count}")
        
        # Eğer istek sayısı 5'ten fazla ise hata döndür
        if current_count and int(current_count) >= 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
        
        # İstek sayısını artır veya yeni bir anahtar oluştur
        if not current_count:
            redis_client.set(key, 1, ex=30)  # 30 saniye için sınır
            print("New key created.")
        else:
            redis_client.incr(key)
            print("Key incremented.")
        
        # İsteği devam ettir
        response = await call_next(request)
        return response
    except HTTPException:
        raise  # HTTP 429 hatasını yeniden yükselt
    except Exception as e:
        print(f"Rate limiting middleware error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

# API Endpoints
@app.post("/register")
def register(user: User):
    cursor = connection.cursor()
    cursor.execute("INSERT INTO USERACCOUNTS (USERNAME, PASSWORD, ROLE) VALUES (:1, :2, :3)", 
                   (user.username, user.password, user.role))
    connection.commit()
    return {"message": "User registered successfully"}

@app.post("/login")
def login(username: str, password: str):
    cursor = connection.cursor()
    cursor.execute("SELECT USER_ID FROM USERACCOUNTS WHERE USERNAME = :1 AND PASSWORD = :2", (username, password))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = str(hash(f"{username}{password}"))
    redis_client.set(token, user[0])
    return {"token": token}

@app.post("/jobs")
def create_job(job: Job, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_create_job():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create jobs")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO JOBS (TITLE, DESCRIPTION, DEPARTMENT) VALUES (:1, :2, :3)", 
                   (job.title, job.description, job.department))
    connection.commit()
    return {"message": "Job created successfully"}

@app.post("/apply")
def apply_for_job(application: Application, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_apply_for_job():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to apply for jobs")
    cursor = connection.cursor()
    cursor.execute("INSERT INTO APPLICATIONS (USER_ID, JOB_ID, STATUS) VALUES (:1, :2, :3)", 
                   (application.user_id, application.job_id, application.status))
    connection.commit()
    return {"message": "Application submitted successfully"}

@app.get("/jobs")
def get_jobs(current_user: BaseUser = Depends(get_current_user)):
    cursor = connection.cursor()
    cursor.execute("SELECT JOB_ID, TITLE, DESCRIPTION, DEPARTMENT FROM JOBS")
    jobs = cursor.fetchall()
    return {"jobs": jobs}

@app.get("/applications")
def get_applications(current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_review_applications():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review applications")
    cursor = connection.cursor()
    cursor.execute("SELECT APPLICATION_ID, USER_ID, JOB_ID, STATUS FROM APPLICATIONS")
    applications = cursor.fetchall()
    return {"applications": applications}

@app.post("/interviews")
def schedule_interview(interview: Interview, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_review_applications():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to schedule interviews")
    
    # Convert interview_date to Oracle TIMESTAMP format
    interview_date = datetime.fromisoformat(interview.interview_date)
    
    cursor = connection.cursor()
    cursor.execute("INSERT INTO INTERVIEWS (USER_ID, JOB_ID, INTERVIEW_DATE, INTERVIEW_RESULT) VALUES (:1, :2, :3, :4)", 
                   (interview.user_id, interview.job_id, interview_date, interview.interview_result))
    connection.commit()
    return {"message": "Interview scheduled successfully"}

@app.get("/interviews")
def get_interviews(current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_review_applications():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view interviews")
    cursor = connection.cursor()
    cursor.execute("SELECT INTERVIEW_ID, USER_ID, JOB_ID, INTERVIEW_DATE, INTERVIEW_RESULT FROM INTERVIEWS")
    interviews = cursor.fetchall()
    return {"interviews": interviews}

# PUT Endpoints
@app.put("/jobs/{job_id}")
def update_job(job_id: int, job: Job, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_update():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update jobs")
    cursor = connection.cursor()
    cursor.execute("UPDATE JOBS SET TITLE = :1, DESCRIPTION = :2, DEPARTMENT = :3 WHERE JOB_ID = :4", 
                   (job.title, job.description, job.department, job_id))
    connection.commit()
    return {"message": "Job updated successfully"}

@app.put("/applications/{application_id}")
def update_application(application_id: int, application: Application, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_update():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update applications")
    cursor = connection.cursor()
    cursor.execute("UPDATE APPLICATIONS SET USER_ID = :1, JOB_ID = :2, STATUS = :3 WHERE APPLICATION_ID = :4", 
                   (application.user_id, application.job_id, application.status, application_id))
    connection.commit()
    return {"message": "Application updated successfully"}

@app.put("/interviews/{interview_id}")
def update_interview(interview_id: int, interview: Interview, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_update():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update interviews")
    
    # Convert interview_date to Oracle TIMESTAMP format
    interview_date = datetime.fromisoformat(interview.interview_date)
    
    cursor = connection.cursor()
    cursor.execute("UPDATE INTERVIEWS SET USER_ID = :1, JOB_ID = :2, INTERVIEW_DATE = :3, INTERVIEW_RESULT = :4 WHERE INTERVIEW_ID = :5", 
                   (interview.user_id, interview.job_id, interview_date, interview.interview_result, interview_id))
    connection.commit()
    return {"message": "Interview updated successfully"}

# DELETE Endpoints
@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_delete():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete jobs")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM JOBS WHERE JOB_ID = :1", (job_id,))
    connection.commit()
    return {"message": "Job deleted successfully"}

@app.delete("/applications/{application_id}")
def delete_application(application_id: int, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_delete():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete applications")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM APPLICATIONS WHERE APPLICATION_ID = :1", (application_id,))
    connection.commit()
    return {"message": "Application deleted successfully"}

@app.delete("/interviews/{interview_id}")
def delete_interview(interview_id: int, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_delete():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete interviews")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM INTERVIEWS WHERE INTERVIEW_ID = :1", (interview_id,))
    connection.commit()
    return {"message": "Interview deleted successfully"}

# USERACCOUNTS Endpoints (Only Admin)
@app.put("/users/{user_id}")
def update_user(user_id: int, user: User, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_manage_users():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update users")
    cursor = connection.cursor()
    cursor.execute("UPDATE USERACCOUNTS SET USERNAME = :1, PASSWORD = :2, ROLE = :3 WHERE USER_ID = :4", 
                   (user.username, user.password, user.role, user_id))
    connection.commit()
    return {"message": "User updated successfully"}

@app.delete("/users/{user_id}")
def delete_user(user_id: int, current_user: BaseUser = Depends(get_current_user)):
    if not current_user.can_manage_users():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete users")
    
    cursor = connection.cursor()
    
    # Delete related records in APPLICATIONS table
    cursor.execute("DELETE FROM APPLICATIONS WHERE USER_ID = :1", (user_id,))
    
    # Delete related records in INTERVIEWS table
    cursor.execute("DELETE FROM INTERVIEWS WHERE USER_ID = :1", (user_id,))
    
    # Now delete the user
    cursor.execute("DELETE FROM USERACCOUNTS WHERE USER_ID = :1", (user_id,))
    
    connection.commit()
    return {"message": "User and all related records deleted successfully"}