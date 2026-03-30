"""S3 + CloudFront for newsradar_front (static SPA)."""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class FrontendStack(Stack):
    """S3 static hosting + CloudFront distribution for newsradar_front.

    Requisitos: 10.1
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for static SPA assets
        self.site_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name="news-radar-sbx-frontend",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # CloudFront distribution
        self.distribution = cloudfront.Distribution(
            self,
            "FrontendDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.site_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            # SPA fallback: return index.html for 404s
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                )
            ],
        )
