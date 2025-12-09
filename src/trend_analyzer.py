"""
Trend Analyzer Module

Loads all historical sitrep JSON files, analyzes trends across time and districts,
and generates AI-powered operational summaries using DeepSeek (with OpenAI fallback).
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import requests

# Try to load dotenv for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def load_all_sitreps(sitreps_dir: Path) -> list[dict]:
    """
    Load all sitrep JSON files from the sitreps directory.
    
    Args:
        sitreps_dir: Path to the directory containing sitrep JSON files
        
    Returns:
        List of sitrep dictionaries sorted by report_date (oldest first)
    """
    sitreps = []
    
    # Find all sitrep_*.json files (exclude latest.json and previous.json)
    for json_file in sitreps_dir.glob("sitrep_*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Add filename for reference
                data["_filename"] = json_file.name
                sitreps.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {json_file}: {e}")
            continue
    
    # Sort by report_date
    def get_report_date(sitrep):
        try:
            date_str = sitrep.get("metadata", {}).get("report_date", "")
            return datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            return datetime.min
    
    sitreps.sort(key=get_report_date)
    
    return sitreps


def build_trend_data(sitreps: list[dict]) -> dict:
    """
    Build structured trend data from a list of sitreps.
    
    Args:
        sitreps: List of sitrep dictionaries sorted by date
        
    Returns:
        Dictionary containing trend analysis data
    """
    if not sitreps:
        return {"error": "No sitrep data available"}
    
    # Key metrics to track
    key_metrics = [
        "deaths", "missing", "people_affected", "families_affected",
        "families_displaced", "people_displaced",
        "houses_fully_damaged", "houses_partially_damaged", "safety_centers"
    ]
    
    # Build time series data
    time_series = []
    
    for sitrep in sitreps:
        metadata = sitrep.get("metadata", {})
        districts = sitrep.get("districts", [])
        
        # Calculate totals
        totals = {metric: 0 for metric in key_metrics}
        district_breakdown = {}
        
        for district in districts:
            district_name = district.get("district", "Unknown")
            district_breakdown[district_name] = {}
            
            for metric in key_metrics:
                value = district.get(metric, 0) or 0
                totals[metric] += value
                district_breakdown[district_name][metric] = value
        
        time_series.append({
            "report_date": metadata.get("report_date", ""),
            "report_date_formatted": metadata.get("report_date_formatted", ""),
            "totals": totals,
            "districts": district_breakdown,
            "num_districts": len(districts)
        })
    
    # Calculate deltas between consecutive reports
    deltas = []
    for i in range(1, len(time_series)):
        current = time_series[i]
        previous = time_series[i - 1]
        
        delta = {
            "from_date": previous["report_date_formatted"],
            "to_date": current["report_date_formatted"],
            "total_changes": {},
            "district_changes": {}
        }
        
        # Total changes
        for metric in key_metrics:
            prev_val = previous["totals"].get(metric, 0)
            curr_val = current["totals"].get(metric, 0)
            change = curr_val - prev_val
            if change != 0:
                delta["total_changes"][metric] = {
                    "previous": prev_val,
                    "current": curr_val,
                    "change": change,
                    "percent_change": round((change / prev_val * 100), 1) if prev_val > 0 else None
                }
        
        # District-level changes for key metrics (deaths, missing, displaced)
        critical_metrics = ["deaths", "missing", "people_displaced", "houses_fully_damaged"]
        all_districts = set(current["districts"].keys()) | set(previous["districts"].keys())
        
        for district in all_districts:
            curr_dist = current["districts"].get(district, {})
            prev_dist = previous["districts"].get(district, {})
            
            district_delta = {}
            for metric in critical_metrics:
                prev_val = prev_dist.get(metric, 0)
                curr_val = curr_dist.get(metric, 0)
                change = curr_val - prev_val
                if change != 0:
                    district_delta[metric] = change
            
            if district_delta:
                delta["district_changes"][district] = district_delta
        
        deltas.append(delta)
    
    # Get latest totals and identify most affected districts
    latest = time_series[-1] if time_series else {}
    latest_districts = latest.get("districts", {})
    
    # Rank districts by key metrics
    district_rankings = {}
    for metric in ["deaths", "missing", "people_affected", "people_displaced"]:
        ranked = sorted(
            [(name, data.get(metric, 0)) for name, data in latest_districts.items()],
            key=lambda x: x[1],
            reverse=True
        )
        district_rankings[metric] = ranked[:5]  # Top 5
    
    return {
        "num_reports": len(sitreps),
        "date_range": {
            "earliest": time_series[0]["report_date_formatted"] if time_series else None,
            "latest": time_series[-1]["report_date_formatted"] if time_series else None
        },
        "latest_totals": latest.get("totals", {}),
        "time_series": time_series,
        "deltas": deltas,
        "district_rankings": district_rankings,
        "num_districts": latest.get("num_districts", 0)
    }


def _build_prompt(trend_data: dict) -> str:
    """Build the prompt for LLM analysis."""
    
    prompt = """You are an expert humanitarian analyst for the ERCC (European Civil Protection and Humanitarian Aid Operations). 
Analyze the following disaster situation data from Sri Lanka and provide a concise operational summary.

## DATA SUMMARY

"""
    
    # Add overview
    prompt += f"**Reports analyzed:** {trend_data['num_reports']} situation reports\n"
    prompt += f"**Date range:** {trend_data['date_range']['earliest']} to {trend_data['date_range']['latest']}\n"
    prompt += f"**Districts affected:** {trend_data['num_districts']}\n\n"
    
    # Add latest totals
    prompt += "### Latest National Totals\n"
    totals = trend_data.get("latest_totals", {})
    prompt += f"- Deaths: {totals.get('deaths', 0):,}\n"
    prompt += f"- Missing: {totals.get('missing', 0):,}\n"
    prompt += f"- People affected: {totals.get('people_affected', 0):,}\n"
    prompt += f"- People displaced: {totals.get('people_displaced', 0):,}\n"
    prompt += f"- Houses fully damaged: {totals.get('houses_fully_damaged', 0):,}\n"
    prompt += f"- Houses partially damaged: {totals.get('houses_partially_damaged', 0):,}\n"
    prompt += f"- Active safety centers: {totals.get('safety_centers', 0):,}\n\n"
    
    # Add district rankings
    prompt += "### Most Affected Districts\n"
    rankings = trend_data.get("district_rankings", {})
    
    if rankings.get("deaths"):
        prompt += "**By deaths:** " + ", ".join([f"{d[0]} ({d[1]})" for d in rankings["deaths"][:3]]) + "\n"
    if rankings.get("missing"):
        prompt += "**By missing:** " + ", ".join([f"{d[0]} ({d[1]})" for d in rankings["missing"][:3] if d[1] > 0]) + "\n"
    if rankings.get("people_displaced"):
        prompt += "**By displaced:** " + ", ".join([f"{d[0]} ({d[1]:,})" for d in rankings["people_displaced"][:3]]) + "\n"
    
    # Add recent changes
    if trend_data.get("deltas"):
        prompt += "\n### Recent Changes (Latest Report vs Previous)\n"
        latest_delta = trend_data["deltas"][-1]
        
        for metric, data in latest_delta.get("total_changes", {}).items():
            change = data["change"]
            sign = "+" if change > 0 else ""
            prompt += f"- {metric.replace('_', ' ').title()}: {sign}{change:,}\n"
        
        # Highlight districts with new deaths or missing
        district_changes = latest_delta.get("district_changes", {})
        critical_changes = []
        for district, changes in district_changes.items():
            if changes.get("deaths", 0) > 0 or changes.get("missing", 0) > 0:
                parts = []
                if changes.get("deaths"):
                    parts.append(f"+{changes['deaths']} deaths")
                if changes.get("missing"):
                    parts.append(f"+{changes['missing']} missing")
                critical_changes.append(f"{district}: {', '.join(parts)}")
        
        if critical_changes:
            prompt += "\n**Districts with new casualties:**\n"
            for change in critical_changes[:5]:
                prompt += f"- {change}\n"
    
    prompt += """

## INSTRUCTIONS

Provide a structured operational summary with the following sections. Use markdown formatting.
Keep the summary concise but actionable (300-400 words total).

### 📊 Overall Situation
Brief assessment of the current disaster impact scale and severity.

### 🔴 Districts of Concern
Identify 3-5 priority districts requiring urgent attention and why.

### 📈 Key Trends
Analyze temporal patterns: Is the situation improving, worsening, or stabilizing? 
What metrics show the most significant changes? Are there any data inconsistencies?

### 📋 Operational Notes
2-3 actionable recommendations for humanitarian response prioritization.

Remember: This is for humanitarian coordinators making operational decisions. Be precise and actionable.
"""
    
    return prompt


def _call_deepseek_api(prompt: str, api_key: str) -> Optional[str]:
    """Call DeepSeek API for analysis."""
    
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek API error: {e}")
        return None


def _call_openai_api(prompt: str, api_key: str) -> Optional[str]:
    """Call OpenAI API as fallback."""
    
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1500
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    except requests.exceptions.RequestException as e:
        print(f"OpenAI API error: {e}")
        return None


def generate_trend_summary(sitreps_dir: Path) -> dict:
    """
    Generate an AI-powered trend analysis summary.
    
    Args:
        sitreps_dir: Path to the directory containing sitrep JSON files
        
    Returns:
        Dictionary with 'success', 'summary', 'provider', and optional 'error' keys
    """
    # Load and analyze data
    sitreps = load_all_sitreps(sitreps_dir)
    
    if not sitreps:
        return {
            "success": False,
            "summary": None,
            "error": "No situation reports found. Please refresh the data first."
        }
    
    if len(sitreps) < 2:
        return {
            "success": False,
            "summary": None,
            "error": "At least 2 situation reports are needed for trend analysis. Currently only 1 report available."
        }
    
    trend_data = build_trend_data(sitreps)
    prompt = _build_prompt(trend_data)
    
    # Try DeepSeek first
    deepseek_key = os.getenv("DEEP_SEEK_API_KEY")
    if deepseek_key:
        summary = _call_deepseek_api(prompt, deepseek_key)
        if summary:
            return {
                "success": True,
                "summary": summary,
                "provider": "DeepSeek",
                "num_reports": len(sitreps),
                "date_range": trend_data["date_range"]
            }
    
    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        summary = _call_openai_api(prompt, openai_key)
        if summary:
            return {
                "success": True,
                "summary": summary,
                "provider": "OpenAI",
                "num_reports": len(sitreps),
                "date_range": trend_data["date_range"]
            }
    
    # Both failed
    return {
        "success": False,
        "summary": None,
        "error": "Unable to generate summary. API keys may be missing or invalid. Please check DEEP_SEEK_API_KEY or OPENAI_API_KEY environment variables."
    }
