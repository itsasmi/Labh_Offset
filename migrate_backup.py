from database import engine, Base
import models

def migrate():
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
