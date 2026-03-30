"""S3 bucket news-radar-sbx-artifacts (SSE-S3) + Secrets Manager."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class StorageStack(Stack):
    """S3 artifacts bucket with prefix structure + Secrets Manager secrets.

    Requisitos: 10.4, 10.5, 10.10
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket with SSE-S3 encryption
        self.artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name="news-radar-sbx-artifacts",
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Prefix structure is implicit in S3 — objects are created under:
        # aras/, riesgos/, vigilancia/weekly/, vigilancia/historical/,
        # search/, reports/

        # Secrets Manager: github-token
        self.github_token_secret = secretsmanager.Secret(
            self,
            "GithubTokenSecret",
            secret_name="news-radar/github-token",
            description="GitHub personal access token for search agent",
        )

        # Secrets Manager: smtp-config
        self.smtp_config_secret = secretsmanager.Secret(
            self,
            "SmtpConfigSecret",
            secret_name="news-radar/smtp-config",
            description="SMTP configuration for newsletter delivery",
        )
