from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel, select


ModelT = TypeVar("ModelT", bound=SQLModel)


class CRUDBase(Generic[ModelT]):
    def __init__(self, model: type[ModelT]):
        self.model = model

    def get(self, session: Session, id_: str) -> ModelT | None:
        return session.get(self.model, id_)

    def list(self, session: Session, limit: int = 100, offset: int = 0) -> list[ModelT]:
        return list(session.exec(select(self.model).offset(offset).limit(limit)).all())

    def create(self, session: Session, obj: ModelT) -> ModelT:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj

    def delete(self, session: Session, obj: ModelT) -> None:
        session.delete(obj)
        session.commit()

