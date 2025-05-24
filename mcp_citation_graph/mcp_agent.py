import asyncio
from agents import Agent, Runner
from agents.mcp.server import MCPServerSse


class MCPAgent:
    def __init__(self, mcp_server_urls: list[str] = None):
        self.mcp_server_urls = mcp_server_urls or []
    
    async def _connect(self):
        self.mcp_servers = []
        for url in self.mcp_server_urls:
            server = MCPServerSse(
                params={
                    "transport": "sse",
                    "url": url,
                },
                cache_tools_list=True,
                client_session_timeout_seconds=20,
            )
            try:
                await server.connect()
                self.mcp_servers.append(server)
            except Exception as e:
                print(f"Failed to connect to MCP server {url}: {e}")

    async def _disconnect(self):
        for server in self.mcp_servers:
            try:
                await server.cleanup()
            except Exception as e:
                print(f"Failed to cleanup MCP server: {e}")
    
    async def _run_agent_async(self, messages):
        await self._connect()
        self.agent = Agent(
            name="Paper citation network agent",
            instructions="Use the tools to answer questions about the paper citation network.",
            model="gpt-4o-mini",
            mcp_servers=self.mcp_servers
        )
        result = await Runner.run(self.agent, messages)
        await self._disconnect()
        return result

    def run(self, messages):
        result = asyncio.run(self._run_agent_async(messages))
        return result.final_output
