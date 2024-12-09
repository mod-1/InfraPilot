# InfraPilot

Setup the repository by cloning it and running the following commands (make sure you have access to https://github.com/taha-junaid/InfraPilot):

```
cd infrastructure_api
pip install -r requirements.txt
git submodule update --init --recursive
```

Get the .env file from the team and place it in the /infrastructure_api directory of the project.

Run the server locally with the following command:

```
python3 manage.py runserver
```

To run it in docker, use the following command:

```
docker compose up --build
```
