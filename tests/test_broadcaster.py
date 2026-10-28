#!/usr/bin/env python3
"""
Unit test suite for social-broadcast-engine.
Validates multi-topic content classification, Bluesky facets,
Mastodon REST endpoints, length safety, and RSS ingestion.
"""

import unittest
from unittest.mock import patch, MagicMock
import json

import broadcast_engine
from content_classifier import classify_content, build_utm_link
import organic_broadcaster

class TestContentClassifier(unittest.TestCase):
    def test_ai_ethics_society_classification(self):
        title = "AI Ethics Case Studies: Lessons Learned from Real-World Failures"
        content = "Examining human rights, strict corporate liability, and algorithmic bias under the EU AI Act."
        topic, tags, hook, cta = classify_content(title, content)
        self.assertEqual(topic, "ai_ethics_society")
        self.assertIn("#AIEthics", tags)
        self.assertIn("#HumanRights", tags)

    def test_defense_laws_classification(self):
        title = "Switchblade 300 and 600: Loitering Munitions in Modern Warfare"
        content = "An analysis of autonomous weapon systems and loitering munitions on the battlefield."
        topic, tags, hook, cta = classify_content(title, content)
        self.assertEqual(topic, "defense_laws")
        self.assertIn("#LAWS", tags)
        self.assertIn("#DefenseGovernance", tags)
        self.assertTrue(len(hook) > 0)
        self.assertTrue(len(cta) > 0)

    def test_ai_governance_classification(self):
        title = "Sovereign Algorithms: Institutional Design for Frontier AI Governance"
        content = "Exploring AI safety, alignment benchmarks, and superintelligence policy."
        topic, tags, hook, cta = classify_content(title, content)
        self.assertEqual(topic, "ai_governance")
        self.assertIn("#AIGovernance", tags)
        self.assertIn("#AISafety", tags)

    def test_international_law_classification(self):
        title = "The Geneva Conventions and State Responsibility in Cyber Warfare"
        content = "Evaluating international humanitarian law (IHL) and treaty compliance."
        topic, tags, hook, cta = classify_content(title, content)
        self.assertEqual(topic, "international_law")
        self.assertIn("#InternationalLaw", tags)
        self.assertIn("#IHL", tags)

    def test_software_tech_classification(self):
        title = "Building a Fullstack Dashboard with Python and React"
        content = "Architecture patterns for high performance web applications and GitHub actions."
        topic, tags, hook, cta = classify_content(title, content)
        self.assertEqual(topic, "software_tech")
        self.assertIn("#SoftwareEngineering", tags)

    def test_utm_link_builder(self):
        link = "https://aviperera.com/switchblade-300-600/"
        bsky_link = build_utm_link(link, "bluesky")
        masto_link = build_utm_link(link, "mastodon")
        self.assertIn("utm_source=bluesky", bsky_link)
        self.assertIn("utm_source=mastodon", masto_link)
        self.assertTrue(bsky_link.startswith("https://aviperera.com/switchblade-300-600/"))

class TestBroadcasterEngine(unittest.TestCase):
    def test_normalize_mastodon_url(self):
        self.assertEqual(broadcast_engine.normalize_mastodon_url("https://mastodon.social/@username"), "https://mastodon.social")
        self.assertEqual(broadcast_engine.normalize_mastodon_url("https://mastodon.social/web/@avi"), "https://mastodon.social")
        self.assertEqual(broadcast_engine.normalize_mastodon_url("https://mastodon.social/api/v1/statuses"), "https://mastodon.social")
        self.assertEqual(broadcast_engine.normalize_mastodon_url("mastodon.social"), "https://mastodon.social")
        self.assertEqual(broadcast_engine.normalize_mastodon_url("https://fosstodon.org/"), "https://fosstodon.org")

    def test_clean_xml_namespaces(self):
        raw = "<rss><channel><item><content:encoded>Sample text</content:encoded><slash:comments>0</slash:comments></item></channel></rss>"
        cleaned = broadcast_engine.clean_xml_namespaces(raw)
        self.assertIn("<encoded>", cleaned)
        self.assertIn("<comments>", cleaned)
        self.assertNotIn("content:", cleaned)

    def test_clean_text(self):
        raw = "<p>Hello &amp; welcome to &#8217;AI Governance&#8217;!</p>"
        cleaned = broadcast_engine.clean_text(raw)
        self.assertEqual(cleaned, "Hello & welcome to ’AI Governance’!")

    def test_bluesky_length_limit(self):
        post = {
            "title": "Comprehensive Legal Framework Analysis of Autonomous Loitering Munitions and Emerging Treaty Obligations Across International Humanitarian Law and State Sovereignty",
            "link": "https://aviperera.com/very-long-article-slug-about-laws-and-treaties-2026/",
            "excerpt": "This long excerpt discusses multiple implications of autonomous weapon systems and AI governance in contemporary geopolitical dynamics.",
            "categories": ["Law", "AI"]
        }
        text, link, tags = broadcast_engine.format_social_copy(post, "bluesky")
        # Bluesky hard limit is 300 characters
        self.assertLessEqual(len(text), 295)
        self.assertIn(link, text)
        for t in tags:
            self.assertIn(t, text)

    def test_mastodon_length_limit(self):
        post = {
            "title": "Switchblade 300 and 600",
            "link": "https://aviperera.com/switchblade-300-600/",
            "excerpt": "A deep dive into loitering munitions and modern defense architectures.",
            "categories": ["Defense"]
        }
        text, link, tags = broadcast_engine.format_social_copy(post, "mastodon")
        self.assertLessEqual(len(text), 490)
        self.assertIn(link, text)

    def test_bluesky_facets_byte_offsets(self):
        text = "Check this: https://aviperera.com/test #AIGovernance #LAWS"
        link = "https://aviperera.com/test"
        tags = ["#AIGovernance", "#LAWS"]
        facets = broadcast_engine.build_bluesky_facets(text, link, tags)
        self.assertTrue(len(facets) >= 3)
        
        # Verify link facet
        link_facet = [f for f in facets if f["features"][0].get("$type") == "app.bsky.feed.post#link"][0]
        start = link_facet["index"]["byteStart"]
        end = link_facet["index"]["byteEnd"]
        extracted_link = text.encode("utf-8")[start:end].decode("utf-8")
        self.assertEqual(extracted_link, link)

        # Verify tag facets
        tag_facets = [f for f in facets if f["features"][0].get("$type") == "app.bsky.feed.post#tag"]
        self.assertEqual(len(tag_facets), 2)

    @patch("urllib.request.urlopen")
    def test_post_to_mastodon(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = json.dumps({"url": "https://mastodon.social/@avi/123"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        success = broadcast_engine.post_to_mastodon(
            instance_url="https://mastodon.social",
            access_token="fake_token",
            text="New research test",
            idempotency_key="unique_hash_123"
        )
        self.assertTrue(success)

    @patch("urllib.request.urlopen")
    def test_post_to_webhook(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 204
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        success = broadcast_engine.post_to_webhook(
            webhook_url="https://discord.com/api/webhooks/mock/123",
            title="Test",
            link="https://aviperera.com",
            excerpt="Excerpt",
            tags=["#AIGovernance"]
        )
        self.assertTrue(success)

class TestOrganicBroadcaster(unittest.TestCase):
    def test_score_sentence_depth(self):
        from intellectual_axioms import score_sentence_depth
        shallow = "The Unitree H1 and H2 are full-size bipedal humanoid robots built by Unitree Robotics of Hangzhou, China."
        deep = "When algorithmic systems impact fundamental human rights, accountability and strict liability cannot be delegated away."
        self.assertLess(score_sentence_depth(shallow), 0)
        self.assertGreater(score_sentence_depth(deep), 20)

    def test_extract_high_depth_snippets(self):
        sample_html = (
            "<p>Robots are manufactured by various tech startups. "
            "When algorithmic systems are deployed in high-stakes domains like healthcare, explainability is a non-derogable procedural right. "
            "Click here to subscribe. Cookie notice.</p>"
        )
        candidates = organic_broadcaster.extract_high_depth_snippets(sample_html, "Title")
        self.assertTrue(len(candidates) > 0)
        self.assertIn("procedural right", candidates[0][0])

    def test_select_next_organic_post(self):
        state = {"posted_snippets": {}}
        text, tags, key_hash, ptype = organic_broadcaster.select_next_organic_post([], state)
        self.assertTrue(len(text) > 20)
        self.assertLessEqual(len(text), 295)
        self.assertTrue(len(tags) > 0)
        self.assertIn("curated_axiom", ptype)

    @patch("urllib.request.urlopen")
    def test_post_organic_to_bluesky(self, mock_urlopen):
        mock_auth_resp = MagicMock()
        mock_auth_resp.read.return_value = json.dumps({"accessJwt": "test_jwt", "did": "did:plc:test"}).encode("utf-8")
        mock_post_resp = MagicMock()
        mock_post_resp.getcode.return_value = 200

        mock_urlopen.return_value.__enter__.side_effect = [mock_auth_resp, mock_post_resp]

        success = organic_broadcaster.post_organic_to_bluesky(
            identifier="test_handle",
            password="test_pass",
            text="High level philosophical insight text #AIGovernance",
            tags=["#AIGovernance"]
        )
        self.assertTrue(success)

    def test_format_article_thesis(self):
        snippet = "When algorithmic systems impact fundamental rights, human oversight cannot be compromised."
        title = "AI Ethics and Human Rights"
        copy, tags = organic_broadcaster.format_article_thesis(snippet, title, ["Ethics", "Society"])
        self.assertLessEqual(len(copy), 295)
        self.assertIn("— Avi Perera", copy)
        self.assertIn("#AIEthics", tags)

if __name__ == "__main__":
    unittest.main()
