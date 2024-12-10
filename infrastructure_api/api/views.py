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
import random

def create_github_pr(new_file_path,resource,resource_name,file_name, username):
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
            insert_resource(timestamp, resource, resource_name, file_name, username)
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
        username= request.data.get('username','test_user')
        names=get_resource_names_by_type('ec2',username)
        return Response({"message": "Success", "data": { "resource_names": names}}, status=status.HTTP_200_OK)

    def create(self, request):
        data = request.data
        username= data.get('username','test_user')
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ec2.tf')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'ec2_{timestamp}.tf'

        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        resource_name = data.get('ec_instance_name', f'ec2_{timestamp}')
        keys = {
            'ec_instance_name': resource_name,
            'ec2_instance_type': data.get('ec2_instance_type'),
            'ec2_ami_id': data.get('ec2_ami_id'),
        }

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

        return create_github_pr(new_file_path,'ec2',resource_name,new_file_name,username)
    
    @action(detail=False, methods=['delete'], url_path='delete-resource')
    def delete_resource(self, request):
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
        username= data.get('username','test_user')
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

        return create_github_pr(new_file_path,'rds',resource_name,new_file_name,username)
    
def insert_resource(timestamp, resource_type, resource_name, file_name, username):
    with transaction.atomic():  # Ensure transaction is handled atomically
        with connection.cursor() as cursor:
            insert_query = '''
            INSERT INTO resources (timestamp, resource_type, resource_name, file_name, username)
            VALUES (%s, %s, %s, %s, %s);
            '''
            
            # Ensure params are passed as a list or tuple
            params = [timestamp, resource_type, resource_name, file_name, username]

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

def get_resource_names_by_type(resource_type,username):
    """
    Retrieves resource names based on the given resource type.

    :param resource_type: The type of resource to filter by (e.g., 'ec2').
    :return: A list of resource names matching the given resource type.
    """
    with connection.cursor() as cursor:
        query = '''
        SELECT resource_name 
        FROM resources 
        WHERE resource_type = %s AND username=%s;
        '''
        
        cursor.execute(query, [resource_type,username])  # Execute query with the parameter
        rows = cursor.fetchall()  # Fetch all matching rows
        
    # Extract the resource names from the rows
    resource_names = [row[0] for row in rows]
    return resource_names

class ClusterViewSet(viewsets.ViewSet):

    def list(self, request):
        return Response({"message": "Success"})

    def create(self, request):
        required_fields = [
            'github_url', 'number_of_instances', 'user_id', 
            'docker_image_name', 'container_port', 'cluster_name', 
            'healthcheck_endpoint'
        ]
        data = request.data

        # Check for missing fields
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return Response({
                "error": "Missing required fields",
                "missing_fields": missing_fields
            }, status=status.HTTP_400_BAD_REQUEST)

        cpu = data.get('cpu', 256)
        memory = data.get('memory', 512)

        # Validate CPU and Memory
        validation_result = validate_cpu_memory(cpu, memory)

        if not validation_result['valid']:
            return Response({
                "error": validation_result['error'],
                "valid_configs": validation_result['valid_configs']
            }, status=status.HTTP_400_BAD_REQUEST)

        # Terraform file generation logic
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ecs.tf')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'ecs_{timestamp}.tf'
        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        # Prepare replacement keys
        priority = str(random.randint(1, 50000))
        keys = {
            'user_id': data.get('user_id'),
            'github_url': data.get('github_url'),
            'cpu': str(data.get('cpu', "256")),
            'memory': str(data.get('memory', "512")),
            'healthcheck': data.get('healthcheck_endpoint'),
            'docker_image_name': data.get('docker_image_name'),
            'cluster_name': data.get('cluster_name'),
            'container_port': str(data.get('container_port')),
            'desired_count': str(data.get('number_of_instances')),
            'unique_id': timestamp,
            'priority': priority
        }

        try:
            with open(file_path, 'r') as f:
                file_data = f.read()

                # Replace placeholders
                for key, value in keys.items():
                    placeholder = f'{{{key}}}'
                    file_data = re.sub(re.escape(placeholder), value, file_data)

                # Write processed file
                with open(new_file_path, 'w') as tf_file:
                    tf_file.write(file_data)

                print(f"Generated file: {new_file_path}")
                resource_name = keys['user_id']+"_cluster_"+keys['unique_id']
                
                # Example GitHub PR creation
                return create_github_pr(new_file_path, "ecs", resource_name,new_file_name)

        except FileNotFoundError:
            return Response(
                {"error": "Template file not found. Please check the path."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Validation Function
VALID_CONFIGS = {
    "256": [512, 1024, 2048],
    "512": [1024, 2048, 3072, 4096],
    "1024": [2048, 3072, 4096, 5120, 6144, 7168, 8192],
    "2048": list(range(4096, 16385, 1024)),
    "4096": list(range(8192, 30721, 1024))
}

def validate_cpu_memory(cpu, memory):
    cpu_str = str(cpu)

    if cpu_str not in VALID_CONFIGS:
        return {
            "valid": False,
            "error": f"Invalid CPU value {cpu}.",
            "valid_configs": VALID_CONFIGS
        }

    if int(memory) not in VALID_CONFIGS[cpu_str]:
        return {
            "valid": False,
            "error": f"Invalid memory size {memory} MiB for CPU {cpu}.",
            "valid_configs": VALID_CONFIGS[cpu_str]
        }

    return {"valid": True}

