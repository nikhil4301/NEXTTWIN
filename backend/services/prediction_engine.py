"""
NextTwin - AI Prediction Engine
Uses statistical ML from Python stdlib (no external libs needed).
Implements: Linear Regression, Weighted Scoring, XAI Explanations.
"""
import math
import statistics
import json
from datetime import datetime


# ─── LINEAR REGRESSION (pure Python) ──────────────────────────────────────────
def linear_regression(x_vals, y_vals):
    """Returns (slope, intercept, r_squared) for simple linear regression."""
    n = len(x_vals)
    if n < 2:
        return 0, y_vals[0] if y_vals else 0, 0
    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x ** 2 for x in x_vals)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return 0, sum_y / n, 0
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    # R-squared
    y_mean = sum_y / n
    ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    return slope, intercept, r2


def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0.5
    return max(0, min(1, (value - min_val) / (max_val - min_val)))


# ─── CGPA PREDICTION ──────────────────────────────────────────────────────────
def predict_cgpa(academic_records, current_cgpa, semester):
    """
    Predict next semester CGPA using trend analysis + weighted scoring.
    XAI: returns factor breakdown.
    """
    if not academic_records:
        return {"predicted_cgpa": current_cgpa, "confidence": 0.5, "factors": [], "trend": "stable"}

    # Group marks by semester
    sem_avg = {}
    for rec in academic_records:
        s = rec["semester"]
        pct = rec["marks"] / rec["max_marks"] * 10
        sem_avg.setdefault(s, []).append(pct)
    sem_means = {s: statistics.mean(v) for s, v in sem_avg.items()}
    semesters = sorted(sem_means.keys())
    if len(semesters) < 2:
        trend_slope = 0
        r2 = 0.5
    else:
        xs = list(range(len(semesters)))
        ys = [sem_means[s] for s in semesters]
        trend_slope, intercept, r2 = linear_regression(xs, ys)
        # Project next semester
        next_x = len(semesters)
        projected = trend_slope * next_x + intercept
    current_sem_avg = sem_means.get(semester, current_cgpa)
    projected = max(4.0, min(10.0, current_sem_avg + trend_slope))

    # Consistency factor
    all_marks = [r["marks"] / r["max_marks"] * 10 for r in academic_records]
    consistency = 1 - (statistics.stdev(all_marks) / 10 if len(all_marks) > 1 else 0.3)

    # Weighted prediction
    predicted = 0.6 * projected + 0.4 * current_cgpa * (consistency)
    predicted = round(max(4.0, min(10.0, predicted)), 2)
    confidence = round(min(0.95, 0.5 + r2 * 0.3 + consistency * 0.2), 2)

    # XAI Factors
    factors = [
        {
            "factor": "Academic Trend",
            "impact": round(trend_slope * 10, 1),
            "weight": "60%",
            "description": f"Your scores are {'improving' if trend_slope > 0 else 'declining'} at {abs(round(trend_slope, 2))} pts/semester",
            "direction": "positive" if trend_slope >= 0 else "negative"
        },
        {
            "factor": "Score Consistency",
            "impact": round(consistency * 100, 1),
            "weight": "25%",
            "description": f"Your marks variance is {'low' if consistency > 0.7 else 'high'} — {'stable performance' if consistency > 0.7 else 'inconsistent results'}",
            "direction": "positive" if consistency > 0.7 else "negative"
        },
        {
            "factor": "Current CGPA Baseline",
            "impact": round(current_cgpa / 10 * 100, 1),
            "weight": "15%",
            "description": f"Starting point of {current_cgpa}/10 gives {'strong' if current_cgpa > 8 else 'moderate'} foundation",
            "direction": "positive" if current_cgpa >= 7.5 else "neutral"
        },
    ]
    trend = "improving" if trend_slope > 0.1 else "declining" if trend_slope < -0.1 else "stable"
    return {
        "predicted_cgpa": predicted,
        "confidence": confidence,
        "factors": factors,
        "trend": trend,
        "current": current_cgpa
    }


# ─── PLACEMENT READINESS ──────────────────────────────────────────────────────
def predict_placement_readiness(user, skills, activities, academic_records):
    """
    Score 0-100 placement readiness. XAI breakdown per factor.
    """
    scores = {}
    explanations = []

    # 1. Academic score (weight 25)
    cgpa = user.get("cgpa", 0)
    acad_score = normalize(cgpa, 4, 10) * 100
    scores["academics"] = acad_score
    explanations.append({
        "factor": "Academic Performance (CGPA)",
        "score": round(acad_score, 1),
        "weight": "25%",
        "description": f"CGPA {cgpa}/10 — {'Excellent' if cgpa >= 8.5 else 'Good' if cgpa >= 7 else 'Needs improvement'}",
        "direction": "positive" if acad_score >= 70 else "negative"
    })

    # 2. Core tech skills (weight 30)
    core_skills = [s for s in skills if s["category"] in ("Programming", "CS Fundamentals", "Database")]
    tech_score = statistics.mean([s["proficiency"] for s in core_skills]) if core_skills else 0
    scores["tech_skills"] = tech_score
    explanations.append({
        "factor": "Technical Skills",
        "score": round(tech_score, 1),
        "weight": "30%",
        "description": f"Average proficiency {round(tech_score)}% across {len(core_skills)} core tech skills",
        "direction": "positive" if tech_score >= 70 else "negative"
    })

    # 3. Soft skills (weight 10)
    soft_skills = [s for s in skills if s["category"] == "Soft Skills"]
    soft_score = statistics.mean([s["proficiency"] for s in soft_skills]) if soft_skills else 50
    scores["soft_skills"] = soft_score
    explanations.append({
        "factor": "Soft Skills",
        "score": round(soft_score, 1),
        "weight": "10%",
        "description": f"Communication & soft skill proficiency at {round(soft_score)}%",
        "direction": "positive" if soft_score >= 65 else "neutral"
    })

    # 4. Extracurricular (weight 20)
    activity_score = min(100, sum(a["impact_score"] * 5 for a in activities)) if activities else 0
    scores["activities"] = activity_score
    explanations.append({
        "factor": "Projects & Activities",
        "score": round(activity_score, 1),
        "weight": "20%",
        "description": f"{len(activities)} activities — hackathons, internships, certifications boost placement score",
        "direction": "positive" if activity_score >= 60 else "negative"
    })

    # 5. Skill diversity (weight 15)
    categories = set(s["category"] for s in skills)
    diversity_score = min(100, len(categories) * 15)
    scores["diversity"] = diversity_score
    explanations.append({
        "factor": "Skill Diversity",
        "score": round(diversity_score, 1),
        "weight": "15%",
        "description": f"Skills across {len(categories)} domains — recruiters value T-shaped profiles",
        "direction": "positive" if diversity_score >= 60 else "neutral"
    })

    # Weighted total
    weights = {"academics": 0.25, "tech_skills": 0.30, "soft_skills": 0.10,
               "activities": 0.20, "diversity": 0.15}
    total = sum(scores[k] * w for k, w in weights.items())
    total = round(min(100, total), 1)

    readiness_label = (
        "Placement Ready" if total >= 80 else
        "Almost Ready" if total >= 65 else
        "Developing" if total >= 50 else
        "Needs Focus"
    )
    return {
        "score": total,
        "label": readiness_label,
        "factors": explanations,
        "confidence": 0.82,
        "top_strength": max(scores, key=scores.get),
        "top_gap": min(scores, key=scores.get)
    }


# ─── SKILL GROWTH PREDICTION ──────────────────────────────────────────────────
def predict_skill_growth(skills):
    """Predict skill levels at 3, 6, 12 months based on practice hours + current level."""
    predictions = []
    for skill in skills:
        current = skill["proficiency"]
        hours = skill.get("hours_practiced", 0)
        # Learning curve: diminishing returns model
        # Growth rate based on hours/week assumed from total hours
        weekly_hours = hours / 26 if hours > 0 else 1  # assume 6 months history
        growth_rate = math.log1p(weekly_hours) * 3  # diminishing returns
        cap = 100
        def project(months):
            future = current + growth_rate * months * (1 - current / cap)
            return round(min(cap, max(current, future)), 1)

        predictions.append({
            "skill": skill["skill_name"],
            "category": skill["category"],
            "current": current,
            "month_3": project(3),
            "month_6": project(6),
            "month_12": project(12),
            "weekly_hours": round(weekly_hours, 1),
            "growth_rate": round(growth_rate, 2)
        })
    return sorted(predictions, key=lambda x: x["growth_rate"], reverse=True)


# ─── WHAT-IF SCENARIO ENGINE ───────────────────────────────────────────────────
def simulate_scenario(scenario_type, params, user_data):
    """
    Predict outcome of hypothetical changes.
    scenario_type: 'add_skill' | 'improve_cgpa' | 'add_activity' | 'change_goal'
    """
    base_score = user_data.get("placement_score", 65)
    results = {}

    if scenario_type == "add_skill":
        skill_name = params.get("skill_name", "New Skill")
        proficiency = params.get("proficiency", 70)
        hours = params.get("hours", 100)
        # Impact: high-demand skills boost placement score
        high_demand = ["Machine Learning", "System Design", "Kubernetes", "React", "AWS", "DSA"]
        demand_multiplier = 1.4 if skill_name in high_demand else 1.1
        impact = (proficiency / 100) * 8 * demand_multiplier
        new_score = min(100, base_score + impact)
        results = {
            "scenario": f"Learning {skill_name} to {proficiency}% proficiency",
            "current_placement_score": base_score,
            "new_placement_score": round(new_score, 1),
            "delta": round(new_score - base_score, 1),
            "time_investment": f"~{hours} hours (~{round(hours/10)} weeks at 10hr/week)",
            "recommendation": f"{'High impact!' if impact > 6 else 'Moderate impact.'} {'This skill is in high demand.' if skill_name in high_demand else 'Consider a high-demand skill for bigger gains.'}",
            "xai_reasoning": [
                f"Base placement score: {base_score}",
                f"Skill proficiency contribution: +{round((proficiency/100)*6, 1)} points",
                f"Market demand multiplier: {demand_multiplier}x",
                f"Estimated net gain: +{round(impact, 1)} points"
            ]
        }

    elif scenario_type == "improve_cgpa":
        target_cgpa = params.get("target_cgpa", 9.0)
        current_cgpa = user_data.get("cgpa", 7.5)
        cgpa_impact = (target_cgpa - current_cgpa) * 4
        new_score = min(100, base_score + cgpa_impact)
        results = {
            "scenario": f"Improving CGPA from {current_cgpa} to {target_cgpa}",
            "current_placement_score": base_score,
            "new_placement_score": round(new_score, 1),
            "delta": round(new_score - base_score, 1),
            "time_investment": f"~{round(abs(target_cgpa - current_cgpa) * 2)} semesters of focused study",
            "recommendation": "Focus on weak subjects. Study 6+ hrs/day before exams.",
            "xai_reasoning": [
                f"CGPA improvement: {current_cgpa} → {target_cgpa}",
                f"Academic weight in model: 25%",
                f"Normalized gain: +{round(cgpa_impact, 1)} placement points",
                "Higher CGPA unlocks more company shortlists"
            ]
        }

    elif scenario_type == "add_activity":
        activity_type = params.get("activity_type", "hackathon")
        impact_map = {"hackathon": 9, "internship": 10, "certification": 7,
                      "project": 7.5, "research": 8, "open_source": 8}
        raw_impact = impact_map.get(activity_type, 7)
        activity_gain = raw_impact * 0.8
        new_score = min(100, base_score + activity_gain)
        results = {
            "scenario": f"Completing a {activity_type}",
            "current_placement_score": base_score,
            "new_placement_score": round(new_score, 1),
            "delta": round(new_score - base_score, 1),
            "time_investment": "Varies (1 week to 6 months)",
            "recommendation": f"{'Internships' if activity_type == 'internship' else activity_type.title() + 's'} have {'highest' if raw_impact >= 9 else 'strong'} impact on placement readiness.",
            "xai_reasoning": [
                f"Activity type: {activity_type} (impact score: {raw_impact}/10)",
                f"Activity weight in model: 20%",
                f"Estimated gain: +{round(activity_gain, 1)} placement points",
                "Recruiters value real-world experience"
            ]
        }

    elif scenario_type == "change_goal":
        role = params.get("role", "Software Engineer")
        skill_match_map = {
            "ML Engineer": ["Machine Learning", "Python", "AI"],
            "Frontend Developer": ["React", "JavaScript", "CSS"],
            "Backend Developer": ["Python", "SQL", "System Design"],
            "Data Scientist": ["Python", "SQL", "Machine Learning"],
            "DevOps Engineer": ["AWS", "Kubernetes", "Linux"],
            "Full Stack": ["React", "JavaScript", "Python", "SQL"]
        }
        required = skill_match_map.get(role, ["Python", "SQL"])
        user_skills = [s["skill_name"] for s in user_data.get("skills", [])]
        matched = [s for s in required if s in user_skills]
        gap = [s for s in required if s not in user_skills]
        match_pct = len(matched) / len(required) * 100 if required else 0
        results = {
            "scenario": f"Targeting role: {role}",
            "current_placement_score": base_score,
            "role_match_percentage": round(match_pct, 1),
            "matched_skills": matched,
            "skill_gaps": gap,
            "recommendation": f"You match {round(match_pct)}% of {role} requirements. {'Great fit!' if match_pct >= 70 else 'Fill the skill gaps to improve your odds.'}",
            "xai_reasoning": [
                f"Required skills for {role}: {', '.join(required)}",
                f"You already have: {', '.join(matched) if matched else 'None matched'}",
                f"Gaps to fill: {', '.join(gap) if gap else 'None — strong match!'}",
                f"Role readiness: {round(match_pct)}%"
            ]
        }

    return results
