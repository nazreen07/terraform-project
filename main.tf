resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "subnet_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "main_route_table" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}

resource "aws_route_table_association" "subnet_association" {
  subnet_id      = aws_subnet.subnet_1.id
  route_table_id = aws_route_table.main_route_table.id
}

resource "aws_security_group" "sg" {
  name        = "secure_sg"
  description = "Allow SSH and HTTP inbound traffic"
  vpc_id      = aws_vpc.main.id

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

data "aws_ami" "ubuntu_ami" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-amd64-server-*"]
  }
}

resource "aws_s3_bucket" "example" {
  bucket = "nazreens3bucket"
}

resource "aws_launch_template" "ubuntu_launch_template" {
  name          = "ubuntu-launch-template"
  image_id      = data.aws_ami.ubuntu_ami.id
  instance_type = "t2.micro"

  network_interfaces {
    security_groups = [aws_security_group.sg.id]
    subnet_id       = aws_subnet.subnet_1.id
  }
  user_data = base64encode(file("userdata1.sh"))

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_autoscaling_group" "ubuntu_asg" {
  max_size             = 0
  min_size             = 0
  vpc_zone_identifier  = [aws_subnet.subnet_1.id]

  launch_template {
    id      = aws_launch_template.ubuntu_launch_template.id
    version = "$Latest"
  }

  health_check_type         = "EC2"
  health_check_grace_period = 300
  wait_for_capacity_timeout = "0"
  force_delete              = true

  tag {
    key                 = "Name"
    value               = "UbuntuInstance"
    propagate_at_launch = true
  }
}

resource "aws_autoscaling_schedule" "scale_up_am" {
  scheduled_action_name = "scale-up-6am"
  autoscaling_group_name = aws_autoscaling_group.ubuntu_asg.name
  desired_capacity     = 2
  min_size             = 2
  max_size             = 2
  start_time           = "2024-11-10T21:45:00Z"
}

resource "aws_autoscaling_schedule" "scale_down_pm" {
  scheduled_action_name = "scale-down-6pm"
  autoscaling_group_name = aws_autoscaling_group.ubuntu_asg.name
  desired_capacity     = 0
  min_size             = 0
  max_size             = 0
  start_time           = "2024-11-10T21:50:00Z"
}

resource "aws_lambda_function" "ec2_termination_report" {
  filename         = "lambda.zip"
  function_name    = "ec2_termination_report"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda.lambda_handler"
  runtime          = "python3.8"
  timeout          = 300

  environment {
    variables = {
      email_recipients = "banunazreen73@gmail.com"
    }
  }
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action    = "ses:SendEmail"
        Effect    = "Allow"
        Resource  = "*"
      },
      {
        Action    = "ce:GetCostAndUsage"
        Effect    = "Allow"
        Resource  = "*"
      }
    ]
  })
}

resource "aws_cloudwatch_event_rule" "ec2_state_change_rule" {
  name        = "ec2-state-change-rule"
  description = "Trigger Lambda function when an EC2 instance changes state"
  event_pattern = jsonencode({
    "source": ["aws.ec2"],
    "detail-type": ["EC2 Instance State-change Notification"],
    "detail": {
      "state": ["running", "terminated"]
    }
  })
}

resource "aws_cloudwatch_event_target" "ec2_state_change_target" {
  rule = aws_cloudwatch_event_rule.ec2_state_change_rule.name
  arn  = aws_lambda_function.ec2_termination_report.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ec2_termination_report.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_state_change_rule.arn
}
