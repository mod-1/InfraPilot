resource "null_resource" "git_clone_{unique_id}" {
  provisioner "local-exec" {
    command = <<EOT
      set -e

      echo "Cleaning up old source if exists..."
      if [ -d "./app_source_{unique_id}" ]; then
        rm -rf ./app_source_{unique_id}
      fi

      echo "Removing any corrupted Git cache..."
      rm -rf ~/.git/index.lock || true

      echo "Cloning latest repository..."
      git clone {github_url} app_source_{unique_id}

    EOT
  }
  triggers = {
    force_redeploy = timestamp()  # Ensures the resource runs on every apply
  }
}

# Build Docker Image
resource "null_resource" "docker_build_{unique_id}" {
  depends_on = [null_resource.git_clone_{unique_id}]

  provisioner "local-exec" {
    command = <<EOT
      echo "Building Docker image..."
      docker build -t {docker_image_name}:{unique_id} ./app_source_{unique_id}
    EOT
  }
  triggers = {
    force_redeploy = timestamp()  # Ensures the resource runs on every apply
  }
}

# Docker Login to ECR
resource "null_resource" "docker_login_{unique_id}" {
  provisioner "local-exec" {
    command = <<EOT
      echo "Logging into ECR..."
      aws ecr get-login-password --region us-east-1 | \
      docker login --username AWS --password-stdin 183295429874.dkr.ecr.us-east-1.amazonaws.com/cloud-computing-repository
    EOT
  }
  triggers = {
    force_redeploy = timestamp()  # Ensures the resource runs on every apply
  }
}

# Tag Docker Image
resource "null_resource" "docker_tag_{unique_id}" {
  depends_on = [null_resource.docker_build_{unique_id}, null_resource.docker_login_{unique_id}]

  provisioner "local-exec" {
    command = <<EOT
      echo "Tagging Docker image..."
      docker tag {docker_image_name}:{unique_id} \
      183295429874.dkr.ecr.us-east-1.amazonaws.com/cloud-computing-repository:{unique_id}
    EOT
  }
  triggers = {
    force_redeploy = timestamp()  # Ensures the resource runs on every apply
  }
}

# Push Docker Image to ECR
resource "null_resource" "docker_push_{unique_id}" {
  depends_on = [null_resource.docker_tag_{unique_id}]

  provisioner "local-exec" {
    command = <<EOT
      echo "Pushing Docker image to ECR..."
      docker push 183295429874.dkr.ecr.us-east-1.amazonaws.com/cloud-computing-repository:{unique_id}
    EOT
  }
  triggers = {
    force_redeploy = timestamp()  # Ensures the resource runs on every apply
  }
}

resource "aws_lb_target_group" "{user_id}_tg_{unique_id}" {
  name        = "{user_id}-tg-{unique_id}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = "vpc-0c67091a11e555368"
  target_type = "ip"

  health_check {
    path                = "{healthcheck}"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "{user_id}_tg_{unique_id} Target Group"
  }
}

# Path-Based Routing Rule for Service 3
resource "aws_lb_listener_rule" "path_rule_{unique_id}" {
  listener_arn = aws_lb_listener.http.arn
  priority     = {priority}

  condition {
    http_header {
      http_header_name = "x-service-name"
      values           = ["{user_id}_{cluster_name}"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.{user_id}_tg_{unique_id}.arn
  }
}

# ECS Service Definition
module "{user_id}_ecs_{unique_id}" {
  source       = "./modules/ecs"
  cluster_name = "{user_id}_cluster_{unique_id}"
  service_name = "{user_id}_service_{unique_id}"
  task_family  = "{user_id}_family_{unique_id}"
  container_definitions = jsonencode([
    {
      name      = "{user_id}_container_{unique_id}"
      image     = "183295429874.dkr.ecr.us-east-1.amazonaws.com/cloud-computing-repository:{unique_id}"
      cpu       = {cpu}
      memory    = {memory}
      essential = true
      portMappings = [
        {
          containerPort = {container_port}
          hostPort      = 80
        }
      ]
    }
  ])
  execution_role_arn = aws_iam_role.ecs_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  subnets            = ["subnet-0bcf804d5a02f7b2d", "subnet-06fb661cc4bb6993f"]
  cpu                = "{cpu}"
  memory             = "{memory}"
  desired_count      = {desired_count}
  security_group_id  = aws_security_group.ecs_alb_sg.id

  host_based_routing = {
    "user66-service" = {
      target_group_arn = aws_lb_target_group.{user_id}_tg_{unique_id}.arn
      container_name   = "{user_id}_container_{unique_id}"
      container_port   = {container_port}
      hostname         = "api.example.com"
    }
  }

  # Ensure ECS Service waits for ALB and Target Group
  depends_on = [
    aws_lb.ecs_alb,
    aws_lb_target_group.{user_id}_tg_{unique_id},
    aws_lb_listener.http
  ]

}