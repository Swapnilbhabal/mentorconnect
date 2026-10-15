from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

InstituteType = Literal["school", "college", "university", "other"]
ProgramLevel = Literal["UG", "PG"]

INSTITUTE_TYPE_LABELS = {"school": "School", "college": "College", "university": "University", "other": "Other"}


class RegisterIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: Literal["student", "mentor"] = "student"

    # Institute affiliation -- asked of both roles, so admins/mentors/students share one concept
    # of "where are you from" instead of two unrelated sets of fields.
    institute_type: InstituteType | None = None
    institute_name: str | None = Field(default=None, max_length=200)

    # Student-only
    roll_number: str | None = Field(default=None, max_length=50)
    program_level: ProgramLevel | None = None
    year_of_study: str | None = Field(default=None, max_length=20)
    branch: str | None = Field(default=None, max_length=120)

    # Mentor-only
    expertise: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
    # Required when role == "mentor" and institute_type is school/college/university (SRS point 3):
    # the mentor's own institute-issued ID (e.g. "VITCMPN111"), so an admin reviewing a
    # verification request can cross-check it against the uploaded document at a glance.
    institute_unique_id: str | None = Field(default=None, max_length=50)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name", "institute_name", "roll_number", "year_of_study", "branch", "institute_unique_id")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    @model_validator(mode="after")
    def check_institute_fields(self) -> "RegisterIn":
        if self.institute_type is not None and not self.institute_name:
            raise ValueError("institute_name is required once an institute_type is selected.")
        if self.role == "mentor" and self.institute_type in ("school", "college", "university") and not self.institute_unique_id:
            raise ValueError(
                "institute_unique_id is required for mentors affiliated with a school, college or university "
                "(e.g. your institute-issued staff/faculty ID, like 'VITCMPN111')."
            )
        return self


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    avatar_url: str | None = None
    mentor_id: int | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut