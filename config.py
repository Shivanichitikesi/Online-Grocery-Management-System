import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///grocery.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOADED_IMAGES_DEST = os.path.join(os.getcwd(), 'static/uploads/images')
