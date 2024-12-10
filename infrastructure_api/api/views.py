from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.conf import settings
import os
import re
import datetime
import subprocess
import requests

def create_github_pr(new_file_path,resource_name):

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(new_file_path))

    branch_name = f'feature/create-{resource_name}-{timestamp}'

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


class ComputeViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Success"})

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

        return create_github_pr(new_file_path,'ec2')

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

        return create_github_pr(new_file_path,'rds')
    

class EcsViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Success"})

    def create(self, request):
        data = request.data
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ecs.tf')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'rds_{timestamp}.tf'
        print("REACHED HERE1")
        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)
        print("REACHED HERE2")

        keys = {
            'cluster_name': data.get('cluster_name'),
            'service_name': data.get('service_name'),
            'target_group_name': data.get('cluster_name'),
            'user_name':data.get('service_name'),
            'aws_lb_listener_rule_name':data.get('service_name')
        }
        print("REACHED HERE3")

        try:
            with open(file_path, 'r') as f:
                file_data = f.read()

                # Replace placeholders with actual values from keys
                for key, value in keys.items():
                    placeholder = f'{{{key}}}'
                    file_data = re.sub(re.escape(placeholder), value if value else '', file_data)

                # Write processed file
                with open(new_file_path, 'w') as tf_file:
                    tf_file.write(file_data)

                print(f"Generated file: {new_file_path}")
                return new_file_path

        except FileNotFoundError:
            print("Template file not found. Please check the path.")
        except Exception as e:
            print(f"An error occurred: {e}")

        with open(new_file_path, 'w') as tf_file:
            tf_file.write(file_data)

        return Response(
                {"message": "Terraform file created successfully", "file_path": new_file_path},
                status=status.HTTP_201_CREATED
            )


        # return create_github_pr(new_file_path,'rds')