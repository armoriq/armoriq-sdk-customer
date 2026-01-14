#!/usr/bin/env python3
"""
Loan Delegation Workflow Example
=================================

This example demonstrates a realistic loan approval workflow using ArmorIQ SDK,
similar to the loan-agent-backend-aniket implementation.

Workflow:
1. User agent captures loan request plan
2. User agent gets intent token from IAP
3. User agent invokes loan-mcp to check eligibility
4. If approval needed, user agent delegates to approval agent
5. Approval agent uses delegated token to invoke approval action
6. Results flow back through the delegation chain

This mirrors the actual loan-agent-backend workflow with proper IAM context
passing and public key-based delegation.
"""

import asyncio
import logging
import os
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from armoriq_sdk import ArmorIQClient
from armoriq_sdk.models import PlanCapture, IntentToken
from armoriq_sdk.exceptions import MCPInvocationException, DelegationException

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LoanUserAgent:
    """
    User agent that initiates loan requests.
    Similar to loan-agent-backend requester flow.
    """
    
    def __init__(self):
        self.client = ArmorIQClient(
            iap_endpoint=os.getenv("IAP_ENDPOINT", "http://localhost:3001"),
            proxy_endpoints={
                "loan-mcp": os.getenv("LOAN_MCP_PROXY", "http://localhost:3002/loan-mcp"),
            },
            user_id="user-12345",
            agent_id="loan-user-agent",
        )
        self.user_email = "john.doe@example.com"
    
    async def request_loan(
        self,
        customer_id: str,
        loan_amount: float,
        loan_purpose: str,
    ):
        """
        Request a loan with automatic delegation to approval agent if needed.
        
        Args:
            customer_id: Customer identifier
            loan_amount: Requested loan amount
            loan_purpose: Purpose of loan
        """
        logger.info(
            f"Starting loan request: customer={customer_id}, "
            f"amount=${loan_amount:,.2f}, purpose={loan_purpose}"
        )
        
        # Step 1: Capture the plan
        plan_steps = [
            {
                "step": 1,
                "mcp": "loan-mcp",
                "action": "check_eligibility",
                "params": {
                    "customer_id": customer_id,
                    "loan_amount": loan_amount,
                    "user_email": self.user_email,
                },
            },
        ]
        
        # Add approval step if amount > $50,000
        if loan_amount > 50000:
            plan_steps.append({
                "step": 2,
                "mcp": "loan-mcp",
                "action": "approve_loan",
                "params": {
                    "customer_id": customer_id,
                    "loan_amount": loan_amount,
                    "user_email": self.user_email,
                    "requires_delegation": True,
                },
            })
        else:
            plan_steps.append({
                "step": 2,
                "mcp": "loan-mcp",
                "action": "process_loan",
                "params": {
                    "customer_id": customer_id,
                    "loan_amount": loan_amount,
                    "user_email": self.user_email,
                },
            })
        
        plan = PlanCapture(
            description=f"Loan request for ${loan_amount:,.2f} - {loan_purpose}",
            steps=plan_steps,
            user_context={
                "customer_id": customer_id,
                "loan_purpose": loan_purpose,
                "requested_at": datetime.utcnow().isoformat(),
            },
        )
        
        # Step 2: Get intent token from IAP
        logger.info("Getting intent token from IAP...")
        token = self.client.get_intent_token(plan)
        logger.info(
            f"Token received: token_id={token.token_id}, "
            f"expires_at={datetime.fromtimestamp(token.expires_at).isoformat()}"
        )
        
        # Log IAM context from token
        if token.policy_validation:
            allowed_tools = token.policy_validation.get("allowed_tools", [])
            logger.info(f"Allowed tools in policy: {allowed_tools}")
        
        # Step 3: Check eligibility
        logger.info("Checking loan eligibility...")
        try:
            eligibility_result = self.client.invoke(
                mcp="loan-mcp",
                action="check_eligibility",
                intent_token=token,
                params={
                    "customer_id": customer_id,
                    "loan_amount": loan_amount,
                },
                user_email=self.user_email,
            )
            
            logger.info(f"Eligibility check result: {eligibility_result.result}")
            
            if not eligibility_result.result.get("eligible"):
                logger.warning("Customer not eligible for loan")
                return {
                    "status": "rejected",
                    "reason": eligibility_result.result.get("reason", "Not eligible"),
                }
        
        except MCPInvocationException as e:
            logger.error(f"Eligibility check failed: {e}")
            return {"status": "error", "reason": str(e)}
        
        # Step 4: Handle approval or processing
        if loan_amount > 50000:
            # Requires delegation to approval agent
            logger.info("Loan amount > $50k, delegating to approval agent...")
            return await self._delegate_for_approval(
                customer_id, loan_amount, token
            )
        else:
            # Process directly
            logger.info("Processing loan directly...")
            try:
                process_result = self.client.invoke(
                    mcp="loan-mcp",
                    action="process_loan",
                    intent_token=token,
                    params={
                        "customer_id": customer_id,
                        "loan_amount": loan_amount,
                    },
                    user_email=self.user_email,
                )
                
                logger.info("Loan processed successfully")
                return {
                    "status": "approved",
                    "loan_id": process_result.result.get("loan_id"),
                    "details": process_result.result,
                }
            
            except MCPInvocationException as e:
                logger.error(f"Loan processing failed: {e}")
                return {"status": "error", "reason": str(e)}
    
    async def _delegate_for_approval(
        self,
        customer_id: str,
        loan_amount: float,
        token: IntentToken,
    ):
        """
        Delegate to approval agent using public key-based delegation.
        """
        # Generate approval agent's keypair
        # In production, approval agent would have pre-registered public key
        approval_private_key = ed25519.Ed25519PrivateKey.generate()
        approval_public_key = approval_private_key.public_key()
        
        # Serialize public key to hex
        pub_key_bytes = approval_public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        approval_public_key_hex = pub_key_bytes.hex()
        
        logger.info(f"Approval agent public key: {approval_public_key_hex[:32]}...")
        
        try:
            # Create delegation
            delegation_result = self.client.delegate(
                intent_token=token,
                delegate_public_key=approval_public_key_hex,
                validity_seconds=1800,  # 30 minutes
                allowed_actions=["approve_loan"],
                target_agent="loan-approval-agent",
            )
            
            logger.info(
                f"Delegation created: delegation_id={delegation_result.delegation_id}"
            )
            
            # Create approval agent with delegated token
            approval_agent = LoanApprovalAgent(
                delegated_token=delegation_result.delegated_token,
                private_key=approval_private_key,
            )
            
            # Approval agent processes the approval
            approval_result = await approval_agent.approve_loan(
                customer_id, loan_amount
            )
            
            return approval_result
        
        except DelegationException as e:
            logger.error(f"Delegation failed: {e}")
            return {"status": "error", "reason": f"Delegation failed: {str(e)}"}


class LoanApprovalAgent:
    """
    Approval agent that processes loan approvals using delegated tokens.
    Similar to loan-agent-backend approval flow.
    """
    
    def __init__(self, delegated_token: IntentToken, private_key):
        self.client = ArmorIQClient(
            iap_endpoint=os.getenv("IAP_ENDPOINT", "http://localhost:3001"),
            proxy_endpoints={
                "loan-mcp": os.getenv("LOAN_MCP_PROXY", "http://localhost:3002/loan-mcp"),
            },
            user_id="approval-system",
            agent_id="loan-approval-agent",
        )
        self.delegated_token = delegated_token
        self.private_key = private_key
        self.approver_email = "loan.approver@example.com"
    
    async def approve_loan(self, customer_id: str, loan_amount: float):
        """
        Approve loan using delegated authority.
        
        Args:
            customer_id: Customer identifier
            loan_amount: Loan amount to approve
        """
        logger.info(
            f"Approval agent processing: customer={customer_id}, "
            f"amount=${loan_amount:,.2f}"
        )
        
        # Verify delegated token has approval permission
        if self.delegated_token.policy_validation:
            allowed_tools = self.delegated_token.policy_validation.get("allowed_tools", [])
            if "approve_loan" not in allowed_tools:
                logger.error("Delegated token does not have approve_loan permission")
                return {
                    "status": "denied",
                    "reason": "Insufficient permissions in delegated token",
                }
        
        # Invoke approval action with delegated token
        try:
            approval_result = self.client.invoke(
                mcp="loan-mcp",
                action="approve_loan",
                intent_token=self.delegated_token,
                params={
                    "customer_id": customer_id,
                    "loan_amount": loan_amount,
                    "approver_notes": "Approved by delegation workflow",
                },
                user_email=self.approver_email,
            )
            
            logger.info("Loan approved successfully")
            return {
                "status": "approved",
                "loan_id": approval_result.result.get("loan_id"),
                "approved_by": "loan-approval-agent",
                "details": approval_result.result,
            }
        
        except MCPInvocationException as e:
            logger.error(f"Approval failed: {e}")
            return {
                "status": "denied",
                "reason": str(e),
            }


async def main():
    """
    Run the complete loan delegation workflow.
    """
    print("=" * 80)
    print("ArmorIQ Loan Delegation Workflow Demo")
    print("=" * 80)
    print()
    
    # Create user agent
    user_agent = LoanUserAgent()
    
    # Example 1: Small loan (no delegation needed)
    print("\n--- Example 1: Small Loan Request ($25,000) ---")
    result1 = await user_agent.request_loan(
        customer_id="CUST-001",
        loan_amount=25000.00,
        loan_purpose="Home renovation",
    )
    print(f"Result: {result1}")
    
    # Example 2: Large loan (requires delegation)
    print("\n--- Example 2: Large Loan Request ($150,000) ---")
    result2 = await user_agent.request_loan(
        customer_id="CUST-002",
        loan_amount=150000.00,
        loan_purpose="Business expansion",
    )
    print(f"Result: {result2}")
    
    print("\n" + "=" * 80)
    print("Workflow Complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Run the async workflow
    asyncio.run(main())
