resource "aws_lb_target_group" "{target_group_name}" {
  name        = "{target_group_name}"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = "vpc-0c67091a11e555368"
  target_type = "ip"

  health_check {
    path                = "/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "{target_group_name} Target Group"
  }
}

# Path-Based Routing Rule for Service 3
resource "aws_lb_listener_rule" "{aws_lb_listener_rule_name}_path_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 1

  condition {
    path_pattern {
      values = ["/{path_name}/*", "/{path_name}"]
    }
  }

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.{target_group_name}.arn
  }
}

# ECS Service Definition
module "{user_name}" {
  source       = "./modules/ecs"
  cluster_name = "{user_name}-cluster"
  service_name = "{user_name}-service"
  task_family  = "{user_name}-family"
  container_definitions = jsonencode([
    {
      name      = "{user_name}-container"
      image     = "nginx:latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
        }
      ]
    }
  ])
  execution_role_arn = aws_iam_role.ecs_execution_role.arn
  task_role_arn      = aws_iam_role.ecs_task_role.arn
  subnets            = ["subnet-0bcf804d5a02f7b2d", "subnet-06fb661cc4bb6993f"]
  cpu                = "256"
  memory             = "512"
  desired_count      = 2
  security_group_id  = aws_security_group.ecs_alb_sg.id

  host_based_routing = {
    "{user_name}-service" = {
      target_group_arn = aws_lb_target_group.{target_group_name}.arn
      container_name   = "{user_name}-container"
      container_port   = 80
      hostname         = "api.example.com"
    }
  }

  # Ensure ECS Service waits for ALB and Target Group
  depends_on = [
    aws_lb.ecs_alb,
    aws_lb_target_group.{target_group_name},
    aws_lb_listener.http
  ]

}