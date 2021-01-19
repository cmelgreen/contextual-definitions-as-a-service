provider "aws" {
    region = "us-west-2"
}

resource "aws_ecs_cluster" "ctx_defs_cluster" {
    name = "ctx_defs_cluster"
}

resource "aws_cloudwatch_log_group" "ctx_defs_log_group" {
    name = "ctx_defs_log_group"
}

resource "aws_ecs_task_definition" "ctx_defs_task" {
    family                   = "ctx_defs_tasks"
    container_definitions    = <<DEFINITION
[{
	"name": "ctx_defs_tasks",
	"image": "cmelgreen\/contextual-definitions-as-a-service",
	"essential": true,
	"portMappings": [{
		"containerPort": 80,
		"hostPort": 80
	}],
    "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
            "awslogs-group": "${aws_cloudwatch_log_group.ctx_defs_log_group.name}",
            "awslogs-region": "us-west-2",
            "awslogs-stream-prefix": "ecs"
    }}
}]
DEFINITION

    requires_compatibilities = ["FARGATE"] 
    network_mode             = "awsvpc"    
    memory                   = 4096             #fargate only accepts mem and cpu values in certain
    cpu                      = 512              # pairings / rangres
    execution_role_arn       = aws_iam_role.ctx_defs_iam.arn
}

resource "aws_ecs_service" "ctx_defs_service" {
    name            = "ctx_defs_service"
    cluster         = aws_ecs_cluster.ctx_defs_cluster.id
    task_definition = aws_ecs_task_definition.ctx_defs_task.arn 
    launch_type     = "FARGATE"
    desired_count   = 1

    load_balancer {
        target_group_arn = aws_lb_target_group.ctx_defs_tg.arn
        container_name   = aws_ecs_task_definition.ctx_defs_task.family
        container_port   = 80
    }

    network_configuration {
        subnets          = [aws_subnet.public_subnet.id]
        assign_public_ip = true
        security_groups = [ aws_security_group.lb_in_all_out_sg.id ]
    }
}

resource "aws_iam_role" "ctx_defs_iam" {
    name               = "ctx_defs_iam"
    assume_role_policy = data.aws_iam_policy_document.base_ecs_iam.json
}

data "aws_iam_policy_document" "base_ecs_iam" {
    statement {
        actions = ["sts:AssumeRole"]

        principals {
            type        = "Service"
            identifiers = ["ecs-tasks.amazonaws.com"]
        }
    }
}

resource "aws_iam_role_policy_attachment" "ctx_defs_polciy_attachments" {
    role       = aws_iam_role.ctx_defs_iam.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_vpc" "vpc" {
    cidr_block              = "10.0.0.0/16"
    enable_dns_support      = true
    enable_dns_hostnames    = true

    tags = {
        Name = "ctx-defs-aas-vpc"
    }
}

resource "aws_internet_gateway" "igw" {
    vpc_id          = aws_vpc.vpc.id
}

resource "aws_subnet" "public_subnet" {
    vpc_id                  = aws_vpc.vpc.id
    cidr_block              = "10.0.1.0/24"
    map_public_ip_on_launch = true
    availability_zone       = "us-west-2a"
}

resource "aws_route_table" "public_rtb" {
    vpc_id          = aws_vpc.vpc.id

    route {
        cidr_block  = "0.0.0.0/0"
        gateway_id  = aws_internet_gateway.igw.id
    }
}

resource "aws_route_table_association" "public_route_assosciation" {
    route_table_id  = aws_route_table.public_rtb.id
    subnet_id       = aws_subnet.public_subnet.id
}

resource "aws_subnet" "backup_subnet" {
    vpc_id                  = aws_vpc.vpc.id
    cidr_block              = "10.0.2.0/24"
    map_public_ip_on_launch = true
    availability_zone       = "us-west-2b"
}

resource "aws_route_table" "backup_rtb" {
    vpc_id          = aws_vpc.vpc.id

    route {
        cidr_block  = "0.0.0.0/0"
        gateway_id  = aws_internet_gateway.igw.id
    }
}

resource "aws_route_table_association" "backaup_route_association" {
    route_table_id  = aws_route_table.backup_rtb.id
    subnet_id       = aws_subnet.backup_subnet.id
}

resource "aws_security_group" "public_http_sg" {
	name        = "public_http_sg"

    vpc_id = aws_vpc.vpc.id

    ingress { 
        from_port   = 22    
        to_port     = 22
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

	ingress {
		from_port   = 80
		to_port     = 80
		protocol    = "tcp"
		cidr_blocks = ["0.0.0.0/0"]
	}

	egress {
		from_port   = 0
		to_port     = 0
		protocol    = "-1"
		cidr_blocks = ["0.0.0.0/0"]
	}
}

resource "aws_security_group" "lb_in_all_out_sg" {
    name = "lb_in_all_out_sg"
    vpc_id = aws_vpc.vpc.id

    ingress {
        from_port = 0
        to_port   = 0
        protocol  = "-1"
        security_groups = [aws_security_group.public_http_sg.id]
    }

    egress {
        from_port   = 0 
        to_port     = 0 
        protocol    = "-1" 
        cidr_blocks = ["0.0.0.0/0"] 
    }
}

resource "aws_alb" "ctx_defs_lb" {
    name               = "ctx-dfs-lb"
    load_balancer_type = "application"
    subnets = [aws_subnet.public_subnet.id, aws_subnet.backup_subnet.id]

    security_groups = [aws_security_group.public_http_sg.id]
}

resource "aws_lb_target_group" "ctx_defs_tg" {
    name        = "ctx-defs-tg"
    port        = 80
    protocol    = "HTTP"
    target_type = "ip"
    vpc_id      = aws_vpc.vpc.id

    health_check {
        matcher = "200,301,302"
        path = "/status/server"
    }

    depends_on = [aws_alb.ctx_defs_lb]
}

resource "aws_lb_listener" "listener" {
    load_balancer_arn = aws_alb.ctx_defs_lb.arn
    port              = "80"
    protocol          = "HTTP"

    default_action {
        type             = "forward"
        target_group_arn = aws_lb_target_group.ctx_defs_tg.arn
    }
}