from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
import os
import re
import datetime
import subprocess
import requests
import sqlite3
from django.db import connection, transaction

def create_github_pr(new_file_path,resource,resource_name,file_name):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(new_file_path))

    branch_name = f'feature/create-{resource}-{timestamp}'

    try:
        subprocess.run(['git', 'config', 'user.name', 'Api user'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'infrapilot.dev@gmail.com'], check=True)

        repo_owner = 'taha-junaid'
        repo_name = 'InfraPilot'
        github_token = os.environ.get('GITHUB_TOKEN')

        if not github_token:
            return Response({"error": "GitHub token not provided"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        remote_url = f'https://{github_token}@github.com/{repo_owner}/{repo_name}.git'
        subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], check=True)

        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)

        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

        subprocess.run(['git', 'add', os.path.basename(new_file_path)], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add updated Terraform configuration'], check=True)

        subprocess.run(['git', 'push', 'origin', branch_name], check=True)

        headers = {'Authorization': f'token {github_token}'}
        pr_title = f'Added configuration'
        pr_body = 'This PR was automatically created by the API to update the instance configuration.'
        pr_data = {
            'title': pr_title,
            'head': branch_name,
            'base': 'main',
            'body': pr_body
        }
        pr_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls'
        response = requests.post(pr_url, json=pr_data, headers=headers)

        if response.status_code == 201:
            pr_info = response.json()
            pr_url = pr_info.get('html_url')
            insert_resource(timestamp, resource, resource_name, file_name)
            return Response({"message": "Pull request created successfully", "pull_request_url": pr_url}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Failed to create pull request", "details": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except subprocess.CalledProcessError as e:
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'branch', '-D', branch_name], check=True)
        return Response({"error": f"Git command failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        subprocess.run(['git', 'checkout', 'main'], check=True)
        os.chdir(original_dir)

def create_github_pr_delete(new_file_path,resource_name,file_name):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(new_file_path))

    branch_name = f'feature/delete-{resource_name}-{timestamp}'

    try:
        subprocess.run(['git', 'config', 'user.name', 'Api user'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'infrapilot.dev@gmail.com'], check=True)

        repo_owner = 'taha-junaid'
        repo_name = 'InfraPilot'
        github_token = os.environ.get('GITHUB_TOKEN')

        if not github_token:
            return Response({"error": "GitHub token not provided"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        remote_url = f'https://{github_token}@github.com/{repo_owner}/{repo_name}.git'
        subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], check=True)

        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)

        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

        if os.path.exists(new_file_path):
            os.remove(new_file_path)
            subprocess.run(['git', 'rm', new_file_path], check=True)
            subprocess.run(['git', 'commit', '-m', f'Delete {resource_name}'], check=True)
        else:
            return Response({"error": f"File '{new_file_path}' does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        subprocess.run(['git', 'push', 'origin', branch_name], check=True)

        headers = {'Authorization': f'token {github_token}'}
        pr_title = f'Delete configuration'
        pr_body = 'This PR was automatically created by the API to update the instance configuration.'
        pr_data = {
            'title': pr_title,
            'head': branch_name,
            'base': 'main',
            'body': pr_body
        }
        pr_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls'
        response = requests.post(pr_url, json=pr_data, headers=headers)

        if response.status_code == 201:
            pr_info = response.json()
            pr_url = pr_info.get('html_url')
            delete_resource_by_file_name(file_name)
            return Response({"message": "Pull request created successfully", "pull_request_url": pr_url}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": "Failed to create pull request", "details": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except subprocess.CalledProcessError as e:
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'branch', '-D', branch_name], check=True)
        return Response({"error": f"Git command failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        subprocess.run(['git', 'checkout', 'main'], check=True)
        os.chdir(original_dir)


class ComputeViewSet(viewsets.ViewSet):
    def list(self, request):
        names=get_resource_names_by_type('ec2')
        return Response({"message": "Success", "data": { "resource_names": names}}, status=status.HTTP_200_OK)

    def create(self, request):
        data = request.data
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ec2.tf')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'ec2_{timestamp}.tf'

        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        keys = {
            'ec_instance_name': data.get('ec_instance_name'),
            'ec2_instance_type': data.get('ec2_instance_type'),
            'ec2_ami_id': data.get('ec2_ami_id'),
        }

        resource_name = data.get('ec_instance_name', f'ec2_{timestamp}')
        with open(file_path, 'r') as f:
            file_data = f.read()
            file_data = re.sub(
                r'module "ec2_template" \{',
                f'module "ec2_template_{timestamp}" {{',
                file_data
            )
            for key, value in keys.items():
                if value:
                    file_data = re.sub(
                        rf'{key}\s*=\s*".*"', 
                        f'{key} = "{value}"', 
                        file_data
                    )
                else:
                    file_data = re.sub(
                        rf'\s*{key}\s*=\s*".*"', 
                        '',
                        file_data
                    )

        with open(new_file_path, 'w') as tf_file:
            tf_file.write(file_data)

        return create_github_pr(new_file_path,'ec2',resource_name,new_file_name)
    
    @action(detail=False, methods=['delete'], url_path='delete-resource')
    def delete_resource(self, request):
        print("arrived in destroy method2")
        data = request.data
        resource_name = data.get('resource_name')
        if not resource_name:
            return Response({"error": "resource_name is required"}, status=400)

        # Logic to delete the resource
        new_file_name = get_file_name(resource_name)
        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        return create_github_pr_delete(new_file_path, 'ec2', new_file_name)

class StoreViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Success"})

    def create(self, request):
        data = request.data
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/rds.tf')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'rds_{timestamp}.tf'

        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        keys = {
            'db_name': data.get('db_name'),
            'db_engine': data.get('db_engine'),
            'instance_class': data.get('instance_class'),
            'db_storage':data.get('db_storage'),
        }

        resource_name = data.get('db_name', f'rds_{timestamp}')

        with open(file_path, 'r') as f:
            file_data = f.read()
            file_data = re.sub(
                r'module "rds_template" \{',
                f'module "rds_template_{timestamp}" {{',
                file_data
            )
            for key, value in keys.items():
                if value:
                    file_data = re.sub(
                        rf'{key}\s*=\s*".*"', 
                        f'{key} = "{value}"', 
                        file_data
                    )
                else:
                    file_data = re.sub(
                        rf'\s*{key}\s*=\s*".*"', 
                        '',
                        file_data
                    )

        with open(new_file_path, 'w') as tf_file:
            tf_file.write(file_data)

        return create_github_pr(new_file_path,'rds',resource_name,new_file_name)
    
def insert_resource(timestamp, resource_type, resource_name, file_name):
    with transaction.atomic():  # Ensure transaction is handled atomically
        with connection.cursor() as cursor:
            insert_query = '''
            INSERT INTO resources (timestamp, resource_type, resource_name, file_name)
            VALUES (%s, %s, %s, %s);
            '''
            
            # Ensure params are passed as a list or tuple
            params = [timestamp, resource_type, resource_name, file_name]

            # Execute the query with parameters
            cursor.execute(insert_query, params)

def get_file_name(resource_name):
    # Get the cursor to execute raw SQL
    with connection.cursor() as cursor:
        query = '''
            SELECT file_name
            FROM resources
            WHERE resource_name = %s;
        '''
        cursor.execute(query, [resource_name])
        
        # Fetch the result
        row = cursor.fetchone()

        if row:
            return row[0]  # The file_name is in the first column
        else:
            return None
        
def delete_resource_by_file_name(file_name):
    with connection.cursor() as cursor:
        # Raw SQL query to delete the row
        query = '''
            DELETE FROM resources
            WHERE file_name = %s;
        '''
        cursor.execute(query, [file_name])

def get_resource_names_by_type(resource_type):
    """
    Retrieves resource names based on the given resource type.

    :param resource_type: The type of resource to filter by (e.g., 'ec2').
    :return: A list of resource names matching the given resource type.
    """
    with connection.cursor() as cursor:
        query = '''
        SELECT resource_name 
        FROM resources 
        WHERE resource_type = %s;
        '''
        
        cursor.execute(query, [resource_type])  # Execute query with the parameter
        rows = cursor.fetchall()  # Fetch all matching rows
        
    # Extract the resource names from the rows
    resource_names = [row[0] for row in rows]
    return resource_names


