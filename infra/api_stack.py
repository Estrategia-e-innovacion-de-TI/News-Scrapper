"""ECS Fargate for newsradar_back (FastAPI) + ALB + API Gateway."""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct


class ApiStack(Stack):
    """ECS Fargate service for newsradar_back (FastAPI) behind ALB.

    Least-privilege task role: S3 read, Secrets Manager read.

    Requisitos: 10.1, 10.9
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        artifacts_bucket: s3.IBucket,
        log_group: logs.ILogGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECR repository
        self.ecr_repo = ecr.Repository(
            self, "BackEcrRepo", repository_name="newsradar-back"
        )

        # Task role — least-privilege for back component
        task_role = iam.Role(
            self,
            "BackTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        artifacts_bucket.grant_read(task_role)
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=["arn:aws:secretsmanager:*:*:secret:news-radar/*"],
            )
        )

        # ALB + Fargate service
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "BackFargateService",
            vpc=vpc,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo),
                container_port=8000,
                task_role=task_role,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="back", log_group=log_group
                ),
                environment={
                    "ARTIFACTS_BUCKET": artifacts_bucket.bucket_name,
                },
            ),
            public_load_balancer=True,
        )
