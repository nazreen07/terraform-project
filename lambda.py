import json
import boto3
import datetime
import os
from botocore.exceptions import BotoCoreError, ClientError

# Initialize AWS clients
ses_client = boto3.client('ses')
ce_client = boto3.client('ce')  # Cost Explorer client for billing information
ec2_client = boto3.client('ec2')  # EC2 client to check instance uptime

# Environment variable for the email recipients
email_recipients = os.getenv('email_recipients').split(',')

# Lambda function handler
def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))

    # Get EC2 instance ID from the event
    instance_id = event['detail'].get('instance-id', 'N/A')
    print(f"EC2 Instance ID: {instance_id}")

    # Safely get the timestamp with a fallback to event time
    event_time = event['detail'].get('timestamp', event.get('time', 'N/A'))
    if event_time == 'N/A':
        print("Warning: 'timestamp' key not found in event detail; using event time as fallback.")
    else:
        print(f"Instance event timestamp: {event_time}")

    # Check for different state changes
    event_state = event['detail'].get('state', 'N/A')
    if event_state == 'running':
        # Send email when an instance starts running
        body_html = generate_html_body(instance_id, event_time, 'N/A', 'Running')
        send_email("Running - EC2 Instance State Change Report", body_html)
        
    elif event_state == 'terminated':
        # Get the last 24-hour billing data
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=1)
        cost_data = get_billing_data(start_date, end_date)

        # For terminated instances, create and send the email with billing data
        body_html = generate_html_body(instance_id, event_time, cost_data, 'Terminated')
        send_email("Terminated - EC2 Instance State Change Report", body_html)

    return {
        'statusCode': 200,
        'body': json.dumps('Email sent successfully!')
    }

# Function to get the launch time of an EC2 instance
def get_instance_launch_time(instance_id):
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        launch_time = response['Reservations'][0]['Instances'][0]['LaunchTime']
        return launch_time.replace(tzinfo=None)
    except (ClientError, IndexError, KeyError) as error:
        print(f"Error retrieving launch time for instance {instance_id}: {error}")
        return None

# Function to fetch billing data from AWS Cost Explorer
def get_billing_data(start_date, end_date):
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': str(start_date), 'End': str(end_date)},
            Granularity='DAILY',
            Metrics=['AmortizedCost']
        )
        total_cost = 0
        for result in response['ResultsByTime']:
            total_cost += float(result['Total']['AmortizedCost']['Amount'])
        return f"{total_cost:.2f}"  # Return as a formatted string
    except (ClientError, BotoCoreError) as error:
        print(f"Error retrieving billing data: {error}")
        return "N/A"

# Function to generate the HTML body for the email
def generate_html_body(instance_id, event_time, cost_data, event_state):
    return f"""
    <div>
        <h3>EC2 Instance State Change Report</h3>
        <p>Instance ID: <strong>{instance_id}</strong></p>
        <p>Event State: <strong>{event_state}</strong></p>
        <p>Event Timestamp: <strong>{event_time}</strong></p>
        <h4>Billing Summary:</h4>
        <p>Total Cost for the last 24 hours: <strong>${cost_data}</strong></p>
    </div>
    """

# Function to send the email using SES
def send_email(subject, body_html):
    # SES verified email addresses for sending and receiving
    sender_email = "nazreen_banu@outlook.com"
    recipient_emails = email_recipients

    try:
        response = ses_client.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': recipient_emails
            },
            Message={
                'Subject': {
                    'Data': subject
                },
                'Body': {
                    'Html': {
                        'Data': body_html
                    }
                }
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
    except (ClientError, BotoCoreError) as error:
        print(f"Error sending email: {error}")
