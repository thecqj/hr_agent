from typing import Optional

from pydantic import BaseModel


class ContactInfo(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    wechat: Optional[str] = None
    other: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    position: str
    start_date: str
    end_date: Optional[str] = None
    description: str


class ProjectExperience(BaseModel):
    name: str
    role: str
    start_date: str
    end_date: Optional[str] = None
    description: str
    technologies: list[str] = []


class Education(BaseModel):
    school: str
    major: str
    degree: str
    start_date: str
    end_date: Optional[str] = None


class Certificate(BaseModel):
    name: str
    date: Optional[str] = None


class StructuredResume(BaseModel):
    name: str
    work_experience_years: int = 0
    education_level: Optional[str] = None
    contact: ContactInfo = ContactInfo()
    work_experience: list[WorkExperience] = []
    project_experience: list[ProjectExperience] = []
    education: list[Education] = []
    certificates: list[Certificate] = []
    skills: list[str] = []
    self_evaluation: Optional[str] = None
