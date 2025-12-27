import asyncio
from fastmcp import Client


async def test_flowcheck():
    print("Connecting to FlowCheck server...")
    # Using the local file directly as the entry point for stdio client is easier for testing
    async with Client("python -m flowcheck.server") as client:
        print("Connected! Listing tools...")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")

        print("\nCalling get_flow_state('.')...")
        result = await client.call_tool("get_flow_state", arguments={"repo_path": "."})
        print(f"Result: {result}")

        print("\nCalling get_recommendations('.')...")
        result = await client.call_tool("get_recommendations", arguments={"repo_path": "."})
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_flowcheck())
