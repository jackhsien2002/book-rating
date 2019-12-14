# settings.py
from dotenv import load_dotenv
load_dotenv(verbose=True)

# OR, explicitly providing path to '.env'
from pathlib import Path  # python3 only
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

#postgres://jmpsfypggemffz:15adfeb621b1dc34385e5a3f3f314fcb4c135912c30e028f8e57f29326625e42@ec2-174-129-253-180.compute-1.amazonaws.com:5432/dc4dargo0eov6k