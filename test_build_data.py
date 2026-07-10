import unittest

import build_data


class SkillClassificationTests(unittest.TestCase):
    def test_openclaw_queries_cover_plugins_and_skills(self) -> None:
        self.assertIn("topic:openclaw-plugin stars:>2", build_data.QUERIES)
        self.assertIn("topic:openclaw-skill stars:>1", build_data.QUERIES)

    def test_openclaw_plugin_is_indexed_and_categorized(self) -> None:
        repo = {
            "full_name": "Xquik-dev/tweetclaw",
            "name": "tweetclaw",
            "description": "OpenClaw plugin for structured X/Twitter workflows",
            "topics": ["openclaw-plugin", "clawhub", "mcp", "social-media"],
        }

        self.assertTrue(build_data.is_skill(repo))
        self.assertEqual(build_data.categorize(repo), "MCP & Tools")

    def test_openclaw_skill_topic_is_indexed(self) -> None:
        repo = {
            "full_name": "example/research-skill",
            "name": "research-skill",
            "description": "Reusable research workflow",
            "topics": ["openclaw-skill"],
        }

        self.assertTrue(build_data.is_skill(repo))
        self.assertEqual(build_data.categorize(repo), "Commands & Hooks")

    def test_openclaw_topic_does_not_bypass_platform_filter(self) -> None:
        repo = {
            "full_name": "example/desktop-client",
            "name": "desktop-client",
            "description": "Desktop app for OpenClaw plugin management",
            "topics": ["openclaw-plugin"],
        }

        self.assertFalse(build_data.is_skill(repo))


if __name__ == "__main__":
    unittest.main()
