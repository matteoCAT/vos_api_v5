from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
from app.models.user import User
from app.models.user_directory import UserDirectory
from app.schemas.user import UserCreate, UserUpdate
from app.models.company import Company


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """
    CRUD operations for User model with multi-tenant support
    """

    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """
        Get a user by email

        Args:
            db: Database session
            email: User email

        Returns:
            Optional[User]: User instance if found, None otherwise
        """
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """
        Get a user by username

        Args:
            db: Database session
            username: Username

        Returns:
            Optional[User]: User instance if found, None otherwise
        """
        return db.query(User).filter(User.username == username).first()

    def create(self, db: Session, *, obj_in: UserCreate, company_id: Union[str, UUID]) -> User:
        """
        Create a new user with hashed password and add to the central directory

        Args:
            db: Database session
            obj_in: UserCreate schema
            company_id: ID of the company this user belongs to

        Returns:
            User: Created user instance
        """
        # First get the company info to determine the schema
        db.execute(text('SET search_path TO public'))
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company with ID {company_id} not found")

        # Add to user directory in public schema
        user_dir = UserDirectory(
            email=obj_in.email,
            username=obj_in.username,
            company_id=company_id,
            schema_name=company.schema_name
        )
        db.add(user_dir)
        db.commit()

        # Now switch to the company schema to create the actual user
        db.execute(text(f'SET search_path TO {company.schema_name}, public'))

        # Create the user in the company schema
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            hashed_password=get_password_hash(obj_in.password),
            name=obj_in.name,
            surname=obj_in.surname,
            telephone=obj_in.telephone,
            role=obj_in.role,
            role_id=obj_in.role_id,
            is_active=obj_in.is_active if obj_in.is_active is not None else True,
            company_id=company_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
            self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        """
        Update a user and synchronize with user directory if email/username changes

        Args:
            db: Database session
            db_obj: User model instance
            obj_in: UserUpdate schema or dict

        Returns:
            User: Updated user instance
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        # If password is being updated, hash it
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password

        # Check if email or username is being updated
        email_changed = "email" in update_data and update_data["email"] != db_obj.email
        username_changed = "username" in update_data and update_data["username"] != db_obj.username

        # Update the user in their company schema
        updated_user = super().update(db, db_obj=db_obj, obj_in=update_data)

        # If email or username changed, update the user directory as well
        if email_changed or username_changed:
            # Get current schema before switching
            current_schema = db.execute(text("SHOW search_path")).fetchone()[0]

            # Switch to public schema to update the directory
            db.execute(text('SET search_path TO public'))

            # Find and update the directory entry
            user_dir = db.query(UserDirectory).filter(
                (UserDirectory.email == db_obj.email) |
                (UserDirectory.username == db_obj.username)
            ).first()

            if user_dir:
                if email_changed:
                    user_dir.email = update_data["email"]
                if username_changed:
                    user_dir.username = update_data["username"]
                db.add(user_dir)
                db.commit()

            # Switch back to the original schema
            db.execute(text(f'SET search_path TO {current_schema}'))

        return updated_user

    def get_multi_by_company(
            self, db: Session, *, company_id: Union[str, UUID], skip: int = 0, limit: int = 100
    ) -> List[User]:
        """
        Get multiple users for a specific company with pagination

        Args:
            db: Database session
            company_id: Company ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (pagination)

        Returns:
            List[User]: List of user instances
        """
        return db.query(User).filter(User.company_id == company_id).offset(skip).limit(limit).all()

    def delete(self, db: Session, *, user_id: Union[str, UUID]) -> Optional[User]:
        """
        Delete a user and their entry in the user directory

        Args:
            db: Database session
            user_id: ID of the user to delete

        Returns:
            Optional[User]: Deleted user instance if found, None otherwise
        """
        # Get the user to find their email/username
        user = self.get(db, id=user_id)
        if not user:
            return None

        # Remember the current schema
        current_schema = db.execute(text("SHOW search_path")).fetchone()[0]

        # Switch to public schema to delete from directory
        db.execute(text('SET search_path TO public'))

        # Find and delete the directory entry
        user_dir = db.query(UserDirectory).filter(
            (UserDirectory.email == user.email) |
            (UserDirectory.username == user.username)
        ).first()

        if user_dir:
            db.delete(user_dir)
            db.commit()

        # Switch back to company schema
        db.execute(text(f'SET search_path TO {current_schema}'))

        # Delete the actual user
        return super().remove(db, id=user_id)

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            Optional[User]: Authenticated user or None
        """
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """
        Check if user is active

        Args:
            user: User instance

        Returns:
            bool: True if user is active
        """
        return user.is_active


# Create an instance of the CRUD class
user = CRUDUser(User)