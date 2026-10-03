#!/usr/bin/env python3
"""Unit tests for GDELT API client."""

import pytest
from scripts.gdelt_api import (
    GDELTClient,
    GDELTEvent,
    GDELTMention,
    GDELTGKGRecord,
    EventQueryBuilder,
    SA_FILTERS,
    FILTER_AFRIKANER_GENOCIDE,
)


class TestEventQueryBuilder:
    def test_build_simple(self):
        builder = EventQueryBuilder({"theme": "GENOCIDE", "country": "ZA"})
        query = builder.build()
        assert "theme:GENOCIDE" in query
        assert "country:ZA" in query

    def test_build_empty(self):
        builder = EventQueryBuilder({})
        assert builder.build() == ""

    def test_add_filter(self):
        builder = EventQueryBuilder().add_filter("actor", "AFRIFORUM")
        assert "actor:AFRIFORUM" in builder.build()


class TestSAFilters:
    def test_all_filters_present(self):
        expected = [
            "afrikaner_genocide",
            "rsa_usa_diplomatic",
            "usa_visa_sanctions",
            "rsa_iran_russia_alignment",
            "brics_wart_countries",
        ]
        for f in expected:
            assert f in SA_FILTERS

    def test_afrikaner_genocide_filter(self):
        f = FILTER_AFRIKANER_GENOCIDE
        assert "GENOCIDE" in f["theme"]
        assert "FARM_ATTACK" in f["theme"]
        assert f["country"] == "ZA"


class TestGDELTEventParsing:
    def test_from_tsv_row_minimal(self):
        # Minimal valid row (58 columns)
        row = ["test_id"] + [""] * 57
        row[1] = "20240101"      # day
        row[2] = "202401"        # month_year
        row[3] = "2024"          # year
        row[5] = "AFRIFORUM"     # actor1_code
        row[6] = "AfriForum"     # actor1_name
        row[26] = "1823"         # event_code
        row[30] = "5.0"          # goldstein_scale
        row[34] = "-2.5"         # avg_tone
        row[51] = "SF"           # action_geo_country_code
        
        event = GDELTEvent.from_tsv_row(row)
        assert event.global_event_id == "test_id"
        assert event.actor1_name == "AfriForum"
        assert event.event_code == "1823"
        assert event.goldstein_scale == 5.0
        assert event.avg_tone == -2.5
        assert event.action_geo_country_code == "SF"

    def test_from_tsv_row_empty(self):
        row = [""] * 58
        event = GDELTEvent.from_tsv_row(row)
        assert event.global_event_id == ""
        assert event.day == 0
        assert event.goldstein_scale == 0.0


class TestGDELTMentionParsing:
    def test_from_tsv_row(self):
        row = ["evt123", "20240101", "20240101", "1", "News24", "http://example.com", "0.5", "", ""]
        mention = GDELTMention.from_tsv_row(row)
        assert mention.global_event_id == "evt123"
        assert mention.mention_source_name == "News24"
        assert mention.mention_doc_tone == 0.5


class TestGDELTGKGRecordParsing:
    def test_from_tsv_row(self):
        row = ["gkg123", "20240101", "1", "News24", "http://example.com"] + [""] * 28
        row[6] = "CRIME_VIOLENCE"  # v1_themes
        gkg = GDELTGKGRecord.from_tsv_row(row)
        assert gkg.gkg_record_id == "gkg123"
        assert gkg.source_common_name == "News24"
        assert gkg.v1_themes == "CRIME_VIOLENCE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])