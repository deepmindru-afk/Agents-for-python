import pytest
from microsoft_agents.copilotstudio_client import (
    CopilotClient,
    PowerPlatformCloud,
    AgentType
)
from microsoft_agents.activity import (
    Activity
)

BOT_ID = "Bot01"
ENVIRONMENT_ID = "A47151CF-4F34-488F-B377-EBE84E17B478"

class TestCopilotStudioClient:

    @pytest.fixture
    def client(self):
        return pytest.mock.create_autospec(CopilotClient)

    async def test_start_conversation_should_return_activities(self, client):
        response = await client.start_conversation()
        async for activity in response:
            assert activity is not None
            assert isinstance(activity, Activity)

    async def ask_question_should_return_activities(self, client):
        activities = client.ask_questions()
        async for activity in activities:
            assert activity is not None
            assert isinstance(activity, Activity)

    @pytest.mark.parametrize(
        "cloud, bot_type, custom_cloud, conversation_id, expected_result, should_throw",
        [
            [
                PowerPlatformCloud.OTHER,
                AgentType.PUBLISHED,
                "foo.api.com",
                "",
                "https://a47151cf4f34488fb377ebe84e17b47.8.environment.foo.api.com/copilotstudio/dataverse-backed/authenticated/bots/Bot01/conversations?api-version=2022-03-01-preview",
            ],
            [
                PowerPlatformCloud.PRE_PROD,
                AgentType.PUBLISHED,
                "",
                "",
                "https://a47151cf4f34488fb377ebe84e17b47.8.environment.api.preprod.powerplatform.com/copilotstudio/dataverse-backed/authenticated/bots/Bot01/conversations?api-version=2022-03-01-preview",
            ],
            [
                PowerPlatformCloud.PROD,
                AgentType.PUBLISHED,
                "",
                "",
                "https://a47151cf4f34488fb377ebe84e17b4.78.environment.api.powerplatform.com/copilotstudio/dataverse-backed/authenticated/bots/Bot01/conversations?api-version=2022-03-01-preview",
            ],
            [
                PowerPlatformCloud.FIRST_RELEASE,
                AgentType.PUBLISHED,
                "",
                "",
                "https://a47151cf4f34488fb377ebe84e17b4.78.environment.api.powerplatform.com/copilotstudio/dataverse-backed/authenticated/bots/Bot01/conversations?api-version=2022-03-01-preview",
            ],
            [
                PowerPlatformCloud.FIRST_RELEASE,
                AgentType.PUBLISHED,
                "",
                "1234",
                "https://a47151cf4f34488fb377ebe84e17b4.78.environment.api.powerplatform.com/copilotstudio/dataverse-backed/authenticated/bots/Bot01/conversations/1234?api-version=2022-03-01-preview",
            ],
            [
                PowerPlatformCloud.PROD,
                AgentType.PRE_BUILT,
                "",
                "1234",
                "https://a47151cf4f34488fb377ebe84e17b4.78.environment.api.powerplatform.com/copilotstudio/prebuilt/authenticated/bots/Bot01/conversations/1234?api-version=2022-03-01-preview"
            ],
            [
                PowerPlatformCloud.OTHER,
                AgentType.PRE_BUILT,
                "Some+1_ Thing",
                "1234",
                "https://a47151cf4f34488fb377ebe84e17b4.78.environment.api.powerplatform.com/copilotstudio/prebuilt/authenticated/bots/Bot01/conversations/1234?api-version=2022-03-01-preview",
                True
            ]
        ]
    )
    def test_verify_connection_url(self, cloud, bot_type, custom_cloud, conversation_id, expected_result, should_throw=False):
        client = CopilotClient()
        url = client._get_connection_url(cloud, bot_type, custom_cloud, conversation_id)
        assert url == expected_result
        if should_throw:
            with pytest.raises(ValueError):
                client._get_connection_url(cloud, bot_type, custom_cloud, conversation_id)

    @pytest.mark.parametrize(
            "cloud, cloud_base_address, expected_authority",
            [
                (PowerPlatformCloud.Prod, "", "https://api.powerplatform.com/.default", False),
                (PowerPlatformCloud.Preprod, "", "https://api.preprod.powerplatform.com/.default", False),
                (PowerPlatformCloud.Mooncake, "", "https://api.powerplatform.partner.microsoftonline.cn/.default", False),
                (PowerPlatformCloud.FirstRelease, "", "https://api.powerplatform.com/.default", False),
                (PowerPlatformCloud.Other, "fido.com", "https://fido.com/.default", False),
                (PowerPlatformCloud.Unknown, "", "", True)
            ]
    )
    def test_verify_agent_scope_test(self, cloud, cloud_base_address, expected_authority, should_throw=False):
        client = CopilotClient()
        authority = client._get_agent_scope(cloud, cloud_base_address)
        assert authority == expected_authority
        if should_throw:
            with pytest.raises(ValueError):
                client._get_agent_scope(cloud, cloud_base_address)