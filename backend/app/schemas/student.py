from pydantic import BaseModel, Field

from .user import InstituteType, ProgramLevel


class StudentProfileOut(BaseModel):
    institute_type: str | None = None
    institute_type_label: str | None = None
    institute_name: str | None = None
    roll_number: str | None = None
    program_level: str | None = None
    year_of_study: str | None = None
    branch: str | None = None


class StudentProfileUpdate(BaseModel):
    institute_type: InstituteType | None = None
    institute_name: str | None = Field(default=None, max_length=200)
    roll_number: str | None = Field(default=None, max_length=50)
    program_level: ProgramLevel | None = None
    year_of_study: str | None = Field(default=None, max_length=20)
    branch: str | None = Field(default=None, max_length=120)