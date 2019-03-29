import jwt
import config
import csv
from datetime import datetime
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy import Column, DateTime, Boolean, Text, String, Integer, Float, ForeignKey, SmallInteger
from sqlalchemy import create_engine, Unicode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import PasswordType
from passlib.handlers import pbkdf2, md5_crypt
from passlib import hash

Base = declarative_base()

#### TABLES ###

class Admins(Base):
    __tablename__ = 'admins'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(PasswordType(
        schemes=[
            'pbkdf2_sha512',
            'md5_crypt'
        ],
        deprecated=['md5_crypt']
    ), nullable=False)
    fullname = Column(Unicode(100), nullable=False)
    company = Column(Unicode(100))
    description = Column(Text(convert_unicode=True))

    active = Column(Boolean)

    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

class Users(Base):
    __tablename__  = 'users'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    fullname = Column(Unicode(100), nullable=False)
    type = Column(String(50), nullable=False, default='user')
    avatar = Column(Text(convert_unicode=True))
    avatar_id = Column(String(50))
    gender = Column(String(10))
    age = Column(Integer)
    lang = Column(Integer)
    description = Column(Text(convert_unicode=True))
    

    active = Column(Boolean, default=True)

    created_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    last_edited_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

    _references = relationship(
        "References",
        cascade="all,delete",
        back_populates="_user")

    _requests = relationship(
        "Requests",
        cascade="all,delete",
        back_populates="_user")

class Requests(Base):
    __tablename__ = 'requests'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), ForeignKey('users.username', onupdate='cascade'), nullable=False)
    
    prompt = Column(Text(convert_unicode=True))
    expiration = Column(DateTime(timezone=False))
    score = Column(Float(precision=2))
    
    status = Column(SmallInteger) 

    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

    _user = relationship(
        "Users",
        cascade=False,
        back_populates="_requests")
    
    _evaluation = relationship(
        "Evaluations",
        cascade="all,delete",
        uselist=False,
        back_populates="_request")

class Prompts(Base):
    __tablename__ = 'prompts'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(Unicode(200), nullable=False, unique=True)

    created_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    last_edited_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

class References(Base):
    __tablename__ = 'references'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), ForeignKey('users.username', onupdate='cascade'), nullable=False)
    
    prompt = Column(Text(convert_unicode=True), nullable=False)
    audio = Column(Text(convert_unicode=True))
    voiceprint = Column(Text)
    dur = Column(Float(precision=2))
    size = Column(Float(precision=2))
    type = Column(String(10))
    file_id = Column(String(50))

    created_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    last_edited_admin = Column(String(50), ForeignKey('admins.username', onupdate='cascade'))
    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

    _user = relationship(
        "Users",
        cascade=False,
        back_populates="_references")

class Evaluations(Base):
    __tablename__ = 'evaluations'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    request_id = Column(Integer, ForeignKey('requests.id', onupdate='cascade', ondelete='cascade'))

    audio = Column(Text(convert_unicode=True))
    voiceprint = Column(Text(convert_unicode=True))
    dur = Column(Float(precision=2))
    size = Column(Float(precision=2))
    file_id = Column(String(50))
    message_id = Column(String(50))
    
    created_date = Column(DateTime(timezone=False))
    last_edited_date = Column(DateTime(timezone=False))

    _request = relationship(
        "Requests",
        uselist=False,
        cascade="all,delete",
        back_populates="_evaluation")

class Logs(Base):
    __tablename__ = 'logs'
    __table_args__ = { 'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci' }

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50))
    ipadd = Column(String(15))
    action = Column(Text(convert_unicode=True))
    message = Column(Text(convert_unicode=True))
    status_code = Column(Integer)
    created_date = Column(DateTime(timezone=False))

if int(config.database.reset) == 1:
    engine = create_engine(
        '{0}://root:{1}@{2}'.format(
            config.database.type,
            config.database.password,
            config.database.address),
        pool_pre_ping=True)
    engine.execute("DROP DATABASE IF EXISTS " + config.database.dbname)
    engine.execute("CREATE DATABASE " + config.database.dbname)

### START ENGINE ###
engine = create_engine(
    '{0}://root:{1}@{2}/{3}'.format(
        config.database.type,
        config.database.password,
        config.database.address,
        config.database.dbname),
    pool_pre_ping=True, pool_recycle=43200)

Base.metadata.create_all(engine)

Session_factory = sessionmaker(bind=engine, autoflush=False)
Session = scoped_session(Session_factory)

session = Session()
if not session.query(Admins).filter_by(username='admin').first():
    admin = Admins()
    admin.fullname = u'Abbas Khosravani'
    admin.username = 'admin'
    admin.password = 'admin'
    admin.company = u'Dezhafzar'
    admin.active = True
    session.add(admin)
    session.commit()
    session.close()

    user = Users()
    user.fullname = u'Root'
    user.username = 'root'
    user.active = True
    session.add(user)
    session.commit()
    session.close()

    if not session.query(Prompts).all():
        with open('models/text') as f:
            lines = csv.reader(f)
            for line in lines:
                prompt = Prompts()
                prompt.text = line[0].decode('utf8')
                prompt.created_user = "admin"
                session.add(prompt)
                session.commit()
            session.close()
