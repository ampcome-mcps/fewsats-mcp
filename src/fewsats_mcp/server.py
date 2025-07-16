"""
Fewsats MCP Server - A Model Context Protocol server for Fewsats payment integration.

This server provides tools for managing payments, wallet balance, and L402/X402 protocol operations
via the Fewsats API. It implements the MCP stdio transport protocol for seamless integration 
with MCP clients.
"""

import json
from typing import Any, Dict, List
import asyncio
import sys
import os
from dotenv import load_dotenv

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import (
    TextContent,
    Tool,
)

# Import Fewsats core functionality
from fewsats.core import Fewsats


class FewsatsMCPServer:
    """MCP Server for Fewsats payment integration using proper MCP patterns."""
    
    def __init__(self):
        """Initialize the Fewsats MCP server with all tools."""
        # Load environment variables from .env file
        load_dotenv(override=True)
        
        self.server = Server("fewsats-mcp")
        self.fewsats = Fewsats()
        self._setup_tools()
    
    def _handle_response(self, response):
        """Helper method to handle API responses consistently."""
        try: 
            return response.status_code, response.json()
        except: 
            return response.status_code, response.text
    
    def _setup_tools(self):
        """Setup all available tools with their schemas."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools."""
            return [
                # Wallet Management Tools
                Tool(
                    name="balance",
                    description="Retrieve the balance of the user's wallet. You will rarely need to call this unless instructed by the user, or to troubleshoot payment issues. Fewsats will automatically add balance when needed.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="payment_methods",
                    description="Retrieve the user's payment methods. You will rarely need to call this unless instructed by the user, or to troubleshoot payment issues. Fewsats will automatically select the best payment method.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="billing_info",
                    description="Retrieve the user's billing information. Returns billing details including name, address, and other relevant information. This information can also be used as shipping address for purchases.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                
                # Payment Processing Tools
                Tool(
                    name="pay_offer",
                    description="Pays an offer_id from the l402_offers. If payment status is 'needs_review' inform the user he will have to approve it at app.fewsats.com",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "offer_id": {
                                "type": "string", 
                                "description": "String identifier for the offer to pay"
                            },
                            "l402_offer": {
                                "type": "object",
                                "description": "L402 offer object with structure containing offers array, payment_context_token, payment_request_url, and version",
                                "properties": {
                                    "offers": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string", "description": "String identifier for the offer"},
                                                "amount": {"type": "number", "description": "Numeric cost value"},
                                                "currency": {"type": "string", "description": "Currency code"},
                                                "description": {"type": "string", "description": "Text description"},
                                                "title": {"type": "string", "description": "Title of the package"}
                                            },
                                            "required": ["id", "amount", "currency"]
                                        }
                                    },
                                    "payment_context_token": {"type": "string", "description": "Payment context token"},
                                    "payment_request_url": {"type": "string", "description": "Payment URL"},
                                    "version": {"type": "string", "description": "API version"}
                                },
                                "required": ["offers", "payment_context_token", "payment_request_url", "version"]
                            }
                        },
                        "required": ["offer_id", "l402_offer"]
                    }
                ),
                Tool(
                    name="payment_info",
                    description="Retrieve the details of a payment. If payment status is 'needs_review' inform the user he will have to approve it at app.fewsats.com",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pid": {"type": "string", "description": "Payment ID to retrieve information for"}
                        },
                        "required": ["pid"]
                    }
                ),
                
                # X402 Protocol Tools
                Tool(
                    name="create_x402_payment_header",
                    description="Creates a payment header for the X402 protocol. Returns a dict with the payment_header field that must be set in X-PAYMENT header in a x402 http request.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "chain": {
                                "type": "string", 
                                "enum": ["base-sepolia", "base"],
                                "description": "Blockchain network to use for payment"
                            },
                            "x402_payload": {
                                "type": "object",
                                "description": "X402 payload object with accepts array and protocol details",
                                "properties": {
                                    "accepts": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "asset": {"type": "string", "description": "Asset contract address"},
                                                "description": {"type": "string", "description": "Payment description"},
                                                "extra": {
                                                    "type": "object",
                                                    "properties": {
                                                        "name": {"type": "string"},
                                                        "version": {"type": "string"}
                                                    }
                                                },
                                                "maxAmountRequired": {"type": "string", "description": "Maximum amount required"},
                                                "maxTimeoutSeconds": {"type": "number", "description": "Maximum timeout in seconds"},
                                                "mimeType": {"type": "string", "description": "MIME type"},
                                                "network": {"type": "string", "description": "Network identifier"},
                                                "payTo": {"type": "string", "description": "Payment recipient address"},
                                                "resource": {"type": "string", "description": "Resource URL"},
                                                "scheme": {"type": "string", "description": "Payment scheme"}
                                            },
                                            "required": ["asset", "network", "payTo", "resource"]
                                        }
                                    },
                                    "error": {"type": "string", "description": "Error message"},
                                    "x402Version": {"type": "number", "description": "X402 protocol version"}
                                },
                                "required": ["accepts", "x402Version"]
                            }
                        },
                        "required": ["chain", "x402_payload"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Execute a tool with the given arguments."""
            try:
                # Route the tool call to the appropriate function
                if name == "balance":
                    result = self._handle_response(self.fewsats.balance())
                elif name == "payment_methods":
                    result = self._handle_response(self.fewsats.payment_methods())
                elif name == "billing_info":
                    result = self._handle_response(self.fewsats.billing_info())
                elif name == "pay_offer":
                    offer_id = arguments["offer_id"]
                    l402_offer = arguments["l402_offer"]
                    result = self._handle_response(self.fewsats.pay_offer(offer_id, l402_offer))
                elif name == "payment_info":
                    pid = arguments["pid"]
                    result = self._handle_response(self.fewsats.payment_info(pid))
                elif name == "create_x402_payment_header":
                    chain = arguments["chain"]
                    x402_payload = arguments["x402_payload"]
                    result = self._handle_response(self.fewsats.pay_x402_offer(x402_payload, chain))
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Return the result as TextContent
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
                
            except Exception as e:
                # Return error information
                error_result = {
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    async def run(self):
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, 
                write_stream, 
                self.server.create_initialization_options()
            )


def main():
    """Main entry point for the MCP server."""
    
    # Check if we're being run directly or as a module
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Fewsats MCP Server")
        print("A Model Context Protocol server for Fewsats payment integration.")
        print("")
        print("Usage:")
        print("  python -m fewsats_mcp.server")
        print("  or")
        print("  fewsats-mcp")
        print("")
        print("This server provides 6 tools for managing:")
        print("  • Wallet Management (balance, payment methods, billing info)")
        print("  • Payment Processing (pay offers, payment info)")
        print("  • X402 Protocol Support (create payment headers)")
        print("")
        print("The server communicates via stdin/stdout using the MCP protocol.")
        return
    
    # Create and run the server
    server = FewsatsMCPServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\\nServer shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
