# terraform-project

General guidelines:
  1. You can use AWS free tier to work with the assignment.
  2. The outcome of the assignment can be provided with screenshots, or through a demonstration.
Task details:
  1. Using Terraform, create a basic VPC to have a secure AWS infrastructure.
  2. Create an AMI with an Ubuntu OS image.
  3. Create an auto-scaling group with the following requirements:
       a. At the beginning of the day at 6:00 AM, launch at least two EC2 instances with the AMI created in step 2. 
       b. At the end of the day at 6:00 PM, terminate all the EC2 instances which are in running state, and ignore the EC2 instances in which some activity is running.
  4. Create a report of the billing details whenever an EC2 instance is terminated and send the report to a list of email recipients.
  5. (Optional) Create an SNS topic with a list of subscribers. Create an alarm notification through email if an EC2 instance has been up overnight.
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
main.tf Terraform configuration file sets up various AWS resources including a Virtual Private Cloud (VPC), subnets, security groups, EC2 Auto Scaling Group (ASG) with scaling schedules, and a Lambda function for EC2 monitoring

1. VPC Setup
aws_vpc: Creates a VPC with the specified CIDR block (10.0.0.0/16).
aws_subnet: Defines a public subnet within the VPC in availability zone us-east-1a, with IP addresses assigned on launch.
aws_internet_gateway: Provides internet access for resources within the VPC.
aws_route_table and aws_route_table_association: Configures a route table to allow outbound internet access by associating it with the internet gateway and subnet.
2. Security Group
aws_security_group: Creates a security group for SSH (port 22) and HTTP (port 80) access.
Ingress Rules: Allows inbound traffic for SSH and HTTP from any IP.
Egress Rules: Allows all outbound traffic.
3. EC2 AMI Data Source
aws_ami: Fetches the latest Ubuntu AMI (Amazon Machine Image) for EC2 instances, owned by Canonical.
4. EC2 Launch Template and Auto Scaling
aws_launch_template: Sets up a template with t2.micro instance type and the latest Ubuntu AMI. It includes security group and subnet association, detailed monitoring, and uses the userdata1.sh script.
aws_autoscaling_group: Configures an Auto Scaling Group with a capacity of 0 (instances are created only through scheduled scaling).
aws_autoscaling_schedule:
scale_up_am: Schedules the scaling up of instances at 5 AM UTC every day.
scale_down_pm: Schedules scaling down at 5 PM UTC.
5. SNS (Simple Notification Service)
aws_sns_topic: Sets up an SNS topic for EC2 instance state change notifications.
aws_sns_topic_subscription:
Email Subscription: Sends email notifications to banunazreen73@gmail.com on state change events.
Lambda Subscription: Sends events to a Lambda function for further processing.
6. Lambda for EC2 Monitoring and Notifications
aws_lambda_function: Lambda function that monitors EC2 state-change and billing events, with notifications sent via email.
aws_iam_role and aws_iam_role_policy_attachment: Configures permissions for the Lambda function.
aws_iam_role_policy: Grants the Lambda function permissions to send emails, access cost data, describe EC2 instances, and publish SNS messages.
7. CloudWatch Alarm
aws_cloudwatch_metric_alarm: Creates an alarm to notify if the EC2 instance runs over 12 hours based on low CPU utilization (1% threshold).
8. EventBridge for EC2 State Changes
aws_cloudwatch_event_rule: Event rule that triggers on EC2 instance state changes (running or terminated).
aws_cloudwatch_event_target: Directs the event rule to invoke the Lambda function.
aws_lambda_permission: Grants EventBridge permission to trigger the Lambda function.
This setup creates a scalable, automated infrastructure with VPC, subnets, auto-scaling EC2 instances, monitoring, and alerting with SNS notifications, along with a Lambda function for handling state-change events.

-------------------------------------------------------------------------------------------------------------------------------------------

**Lambda Function Code for EC2 State Change and Billing Notifications**

1. Imports and AWS Client Initialization:
The function uses several libraries: json for JSON handling, boto3 for AWS service interactions, datetime for date and time operations, os for environment variables, and botocore.exceptions to manage AWS client errors.
AWS clients are initialized for SES (email), Cost Explorer (billing), and EC2 (instance management).

2. Environment Variable:
The function reads the email_recipients environment variable to determine the list of email recipients for notifications.

3. Lambda Handler (lambda_handler):
This is the main function invoked by AWS Lambda upon an event trigger. It checks if the incoming event is an EC2 instance state-change notification (e.g., instance started or terminated).
For both "running" and "terminated" states, it fetches the last 24 hours of billing data and constructs an HTML email report with details about the instance event and cost.
It sends an email with the report, either indicating that an instance started running or was terminated.

4. Billing Data Retrieval (get_billing_data):
This helper function queries AWS Cost Explorer to obtain the total cost of services over the last 24 hours.
It returns the cost as a formatted string for use in the email, handling any exceptions if billing data cannot be retrieved.

5. HTML Email Body Generation (generate_html_body):
This function generates an HTML-formatted body for the email, including details such as the instance ID, event state, timestamp, and the 24-hour billing summary.
The formatted HTML structure is then included in the email content to make the report user-friendly and visually organized.

6. Sending Email (send_email):
This function uses AWS SES to send the email with the provided subject and HTML body to the specified recipients.
The function includes error handling to capture any issues during email delivery and logs a message if an error occurs.
This Lambda function provides a comprehensive solution for real-time monitoring and notifications of EC2 state changes, enhancing observability and cost-awareness by combining instance state monitoring with recent cost data.

------------------------------------------------------------------------------------------------------------------------------------------

userdata1.sh - has a small code running on Apache.


