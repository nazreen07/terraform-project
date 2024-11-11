import json
import boto3
import datetime
import os
from botocore.exceptions import BotoCoreError, ClientError

# Initialize AWS clients
ses_client = boto3.client('ses')
ce_client = boto3.client('ce')
ec2_client = boto3.client('ec2')

# Environment variable for the email recipients
email_recipients = os.getenv('email_recipients').split(',')

# Lambda function handler
def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))

    # Check if this event is an EC2 state-change event
    if "detail-type" in event and event["detail-type"] == "EC2 Instance State-change Notification":
        instance_id = event['detail'].get('instance-id', 'N/A')
        event_state = event['detail'].get('state', 'N/A')
        event_time = event['time']
        
        # Get the last 24-hour billing data
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=1)
        cost_data = get_billing_data(start_date, end_date)

        # Send email when an instance starts running
        if event_state == 'running':
            body_html = generate_html_body(instance_id, event_time, cost_data, 'Running')
            send_email("Running - EC2 Instance State Change Report", body_html)

        # Send email when an instance is terminated
        elif event_state == 'terminated':
            body_html = generate_html_body(instance_id, event_time, cost_data, 'Terminated')
            send_email("Terminated - EC2 Instance State Change Report", body_html)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Event processed successfully!')
    }

# Function to get the last 24-hour billing data from AWS Cost Explorer
def get_billing_data(start_date, end_date):
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={'Start': str(start_date), 'End': str(end_date)},
            Granularity='DAILY',
            Metrics=['AmortizedCost']
        )
        total_cost = sum(float(result['Total']['AmortizedCost']['Amount']) for result in response['ResultsByTime'])
        print(f"Billing data for the last 24 hours: ${total_cost:.2f}")
        return f"{total_cost:.2f}"
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
    sender_email = "nazreen_banu@outlook.com"
    recipient_emails = email_recipients

    try:
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': recipient_emails},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': body_html}}
            }
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
    except (ClientError, BotoCoreError) as error:
        print(f"Error sending email: {error}")
