"""
AI Progress Intelligence System
=============================

Provides intelligent analysis of user progress with personalized recommendations
from Guru and Parikshak agents based on learning patterns and achievements.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)

class SkillLevel(Enum):
    """User skill levels for different competencies"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"
    EXPERT = "expert"

class LearningStyle(Enum):
    """Identified learning preferences"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    KINESTHETIC = "kinesthetic"
    ANALYTICAL = "analytical"

@dataclass
class SkillProgress:
    """Progress tracking for specific skills"""
    skill_name: str
    current_level: SkillLevel
    sessions_count: int
    time_spent_minutes: int
    last_activity: datetime
    improvement_rate: float  # Progress per session
    confidence_score: float  # 0-1, how confident the assessment is
    
@dataclass
class LearningInsight:
    """AI-generated insights about user learning"""
    insight_type: str  # "strength", "weakness", "opportunity", "recommendation"
    title: str
    description: str
    confidence: float
    agent_source: str  # "guru" or "parikshak"
    suggested_actions: List[str] = field(default_factory=list)

@dataclass
class ProgressAnalysis:
    """Comprehensive AI analysis of user progress"""
    candidate_id: str
    overall_progress_score: float  # 0-100
    learning_velocity: float  # Progress rate over time
    engagement_level: str  # "low", "medium", "high"
    primary_learning_style: LearningStyle
    skill_assessments: List[SkillProgress]
    key_insights: List[LearningInsight]
    guru_recommendations: List[str]
    parikshak_recommendations: List[str]
    next_milestone: str
    estimated_completion_time: Optional[str]

class AIProgressIntelligence:
    """AI-powered progress analysis and recommendations"""
    
    def __init__(self):
        self.skill_keywords = {
            "technical": ["programming", "coding", "software", "development", "algorithm", "database", "python", "javascript"],
            "communication": ["presentation", "speaking", "interview", "communication", "english", "hindi", "language"],
            "analytical": ["problem", "analysis", "logic", "reasoning", "math", "statistics", "data"],
            "leadership": ["team", "leader", "management", "project", "collaboration", "decision"],
            "creativity": ["design", "creative", "innovation", "solution", "artistic", "writing"]
        }
        
        # Progress thresholds for different skill levels
        self.level_thresholds = {
            SkillLevel.BEGINNER: (0, 25),
            SkillLevel.INTERMEDIATE: (25, 60),
            SkillLevel.ADVANCED: (60, 85),
            SkillLevel.EXPERT: (85, 100)
        }
    
    async def analyze_progress(self, candidate_id: str, session_data: List[Dict], chat_history: List[Dict]) -> ProgressAnalysis:
        """Perform comprehensive AI analysis of user progress"""
        
        try:
            # Extract learning patterns
            skill_assessments = self._assess_skills(session_data, chat_history)
            learning_style = self._identify_learning_style(chat_history)
            engagement_metrics = self._calculate_engagement(session_data)
            
            # Generate insights
            insights = self._generate_insights(skill_assessments, chat_history, engagement_metrics)
            
            # Create agent-specific recommendations
            guru_recs = self._generate_guru_recommendations(skill_assessments, insights)
            parikshak_recs = self._generate_parikshak_recommendations(skill_assessments, insights)
            
            # Calculate overall metrics
            overall_score = self._calculate_overall_progress(skill_assessments)
            learning_velocity = self._calculate_learning_velocity(session_data)
            
            # Determine next milestone
            next_milestone = self._suggest_next_milestone(skill_assessments, overall_score)
            
            # Estimate completion time
            completion_time = self._estimate_completion_time(learning_velocity, overall_score)
            
            analysis = ProgressAnalysis(
                candidate_id=candidate_id,
                overall_progress_score=overall_score,
                learning_velocity=learning_velocity,
                engagement_level=engagement_metrics["level"],
                primary_learning_style=learning_style,
                skill_assessments=skill_assessments,
                key_insights=insights,
                guru_recommendations=guru_recs,
                parikshak_recommendations=parikshak_recs,
                next_milestone=next_milestone,
                estimated_completion_time=completion_time
            )
            
            logger.info(f"✅ Generated AI progress analysis for {candidate_id}: {overall_score:.1f}% progress")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI progress analysis failed: {e}")
            # Return basic analysis on failure
            return self._create_fallback_analysis(candidate_id)
    
    def _assess_skills(self, session_data: List[Dict], chat_history: List[Dict]) -> List[SkillProgress]:
        """Assess user skills based on interactions"""
        skills = {}
        
        # Analyze chat content for skill indicators
        for message in chat_history:
            if message.get('role') == 'user':
                content = message.get('content', '').lower()
                
                for skill_category, keywords in self.skill_keywords.items():
                    relevance_score = sum(1 for keyword in keywords if keyword in content)
                    
                    if relevance_score > 0:
                        if skill_category not in skills:
                            skills[skill_category] = {
                                'mentions': 0,
                                'sessions': set(),
                                'complexity_indicators': 0
                            }
                        
                        skills[skill_category]['mentions'] += relevance_score
                        skills[skill_category]['sessions'].add(message.get('session_id', 'unknown'))
                        
                        # Assess complexity based on sentence length and terminology
                        if len(content.split()) > 15:  # Longer, more complex responses
                            skills[skill_category]['complexity_indicators'] += 1
        
        # Convert to SkillProgress objects
        skill_assessments = []
        for skill_name, data in skills.items():
            # Calculate skill level based on engagement and complexity
            engagement_score = min(data['mentions'] * 10 + data['complexity_indicators'] * 5, 100)
            
            # Determine skill level
            current_level = SkillLevel.BEGINNER
            for level, (min_score, max_score) in self.level_thresholds.items():
                if min_score <= engagement_score < max_score:
                    current_level = level
                    break
            
            skill_progress = SkillProgress(
                skill_name=skill_name,
                current_level=current_level,
                sessions_count=len(data['sessions']),
                time_spent_minutes=len(data['sessions']) * 15,  # Estimate 15 min per session
                last_activity=datetime.now(),
                improvement_rate=engagement_score / max(len(data['sessions']), 1),
                confidence_score=min(data['mentions'] / 10, 1.0)
            )
            
            skill_assessments.append(skill_progress)
        
        return skill_assessments
    
    def _identify_learning_style(self, chat_history: List[Dict]) -> LearningStyle:
        """Identify primary learning style from interaction patterns"""
        indicators = {
            LearningStyle.VISUAL: ["show", "see", "diagram", "image", "visual", "picture", "chart"],
            LearningStyle.AUDITORY: ["explain", "tell", "hear", "listen", "voice", "audio", "sound"],
            LearningStyle.KINESTHETIC: ["practice", "try", "do", "hands-on", "experience", "exercise"],
            LearningStyle.ANALYTICAL: ["analyze", "logic", "reason", "step", "method", "process", "why", "how"]
        }
        
        scores = {style: 0 for style in LearningStyle}
        
        for message in chat_history:
            if message.get('role') == 'user':
                content = message.get('content', '').lower()
                
                for style, keywords in indicators.items():
                    scores[style] += sum(1 for keyword in keywords if keyword in content)
        
        # Return the style with highest score, default to analytical
        max_style = LearningStyle.ANALYTICAL
        max_score = 0
        for style, score in scores.items():
            if score > max_score:
                max_score = score
                max_style = style
        
        return max_style
    
    def _calculate_engagement(self, session_data: List[Dict]) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        if not session_data:
            return {"level": "low", "score": 0, "consistency": 0}
        
        # Calculate metrics
        total_sessions = len(session_data)
        avg_session_length = sum(s.get('messages_count', 0) for s in session_data) / total_sessions
        
        # Check for consistent activity (sessions over time)
        recent_sessions = sum(1 for s in session_data if 
                            datetime.fromisoformat(s.get('started_at', '2024-01-01')) > datetime.now() - timedelta(days=7))
        
        consistency_score = recent_sessions / min(total_sessions, 7)  # Last 7 days
        
        # Overall engagement calculation
        engagement_score = min((avg_session_length * 2 + consistency_score * 50 + total_sessions), 100)
        
        level = "low"
        if engagement_score > 70:
            level = "high"
        elif engagement_score > 40:
            level = "medium"
        
        return {
            "level": level,
            "score": engagement_score,
            "consistency": consistency_score,
            "avg_session_length": avg_session_length
        }
    
    def _generate_insights(self, skills: List[SkillProgress], chat_history: List[Dict], engagement: Dict) -> List[LearningInsight]:
        """Generate AI insights about learning progress"""
        insights = []
        
        # Engagement insights
        if engagement["level"] == "high":
            insights.append(LearningInsight(
                insight_type="strength",
                title="Excellent Engagement",
                description="You're showing consistent and active learning behavior. Keep up the great momentum!",
                confidence=0.9,
                agent_source="guru",
                suggested_actions=["Continue current learning pace", "Consider tackling more advanced topics"]
            ))
        elif engagement["level"] == "low":
            insights.append(LearningInsight(
                insight_type="opportunity",
                title="Engagement Improvement Needed",
                description="More consistent practice could accelerate your learning progress.",
                confidence=0.8,
                agent_source="guru",
                suggested_actions=["Set daily learning goals", "Schedule regular practice sessions"]
            ))
        
        # Skill-specific insights
        for skill in skills:
            if skill.current_level == SkillLevel.ADVANCED:
                insights.append(LearningInsight(
                    insight_type="strength",
                    title=f"Strong {skill.skill_name.title()} Skills",
                    description=f"Your {skill.skill_name} abilities are well-developed. Ready for expert-level challenges!",
                    confidence=skill.confidence_score,
                    agent_source="parikshak",
                    suggested_actions=[f"Take on leadership roles in {skill.skill_name}", "Mentor others in this area"]
                ))
            elif skill.improvement_rate > 5:
                insights.append(LearningInsight(
                    insight_type="strength",
                    title=f"Rapid {skill.skill_name.title()} Progress",
                    description=f"You're making excellent progress in {skill.skill_name}. Your learning rate is above average!",
                    confidence=skill.confidence_score,
                    agent_source="guru",
                    suggested_actions=[f"Continue focusing on {skill.skill_name}", "Consider advanced topics in this area"]
                ))
        
        return insights
    
    def _generate_guru_recommendations(self, skills: List[SkillProgress], insights: List[LearningInsight]) -> List[str]:
        """Generate Guru's learning recommendations"""
        recommendations = []
        
        # Based on skill gaps
        if not any(skill.current_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT] for skill in skills):
            recommendations.append("Focus on developing one core skill to an advanced level rather than spreading efforts too thin")
        
        # Based on learning patterns
        weak_skills = [skill for skill in skills if skill.improvement_rate < 2]
        if weak_skills:
            recommendations.append(f"Consider alternative learning approaches for {', '.join(s.skill_name for s in weak_skills[:2])}")
        
        # Based on engagement
        low_engagement_insights = [i for i in insights if i.insight_type == "opportunity"]
        if low_engagement_insights:
            recommendations.append("Establish a consistent learning routine with small, achievable daily goals")
        
        # Generic learning advice
        recommendations.extend([
            "Practice active recall by explaining concepts in your own words",
            "Connect new learning to your existing knowledge and experience",
            "Set specific, measurable learning objectives for each session"
        ])
        
        return recommendations[:5]  # Limit to top 5
    
    def _generate_parikshak_recommendations(self, skills: List[SkillProgress], insights: List[LearningInsight]) -> List[str]:
        """Generate Parikshak's interview and assessment recommendations"""
        recommendations = []
        
        # Technical readiness
        technical_skills = [s for s in skills if s.skill_name == "technical"]
        if technical_skills and technical_skills[0].current_level in [SkillLevel.INTERMEDIATE, SkillLevel.ADVANCED]:
            recommendations.append("Practice coding interviews with live problem-solving sessions")
            recommendations.append("Prepare system design scenarios for senior-level positions")
        
        # Communication skills
        comm_skills = [s for s in skills if s.skill_name == "communication"]
        if not comm_skills or comm_skills[0].current_level == SkillLevel.BEGINNER:
            recommendations.append("Practice articulating technical concepts to non-technical audiences")
            recommendations.append("Record yourself explaining complex topics to improve clarity")
        
        # Interview-specific advice
        recommendations.extend([
            "Practice the STAR method (Situation, Task, Action, Result) for behavioral questions",
            "Prepare specific examples that demonstrate problem-solving and leadership",
            "Research company culture and values for targeted interview preparation",
            "Practice mock interviews with gradually increasing difficulty levels"
        ])
        
        return recommendations[:5]  # Limit to top 5
    
    def _calculate_overall_progress(self, skills: List[SkillProgress]) -> float:
        """Calculate overall progress score (0-100)"""
        if not skills:
            return 0.0
        
        # Weight skills by confidence and level
        total_weighted_score = 0
        total_weight = 0
        
        level_scores = {
            SkillLevel.BEGINNER: 25,
            SkillLevel.INTERMEDIATE: 50,
            SkillLevel.ADVANCED: 75,
            SkillLevel.EXPERT: 100
        }
        
        for skill in skills:
            score = level_scores[skill.current_level]
            weight = skill.confidence_score
            total_weighted_score += score * weight
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_learning_velocity(self, session_data: List[Dict]) -> float:
        """Calculate learning velocity (progress per unit time)"""
        if len(session_data) < 2:
            return 1.0  # Default velocity
        
        # Sort sessions by date
        sorted_sessions = sorted(session_data, key=lambda x: datetime.fromisoformat(x.get('started_at', '2024-01-01')))
        
        # Calculate time span and message growth
        time_span = (datetime.fromisoformat(sorted_sessions[-1]['started_at']) - 
                    datetime.fromisoformat(sorted_sessions[0]['started_at'])).days
        
        if time_span == 0:
            return 1.0
        
        message_growth = sum(s.get('messages_count', 0) for s in sorted_sessions[-3:]) - sum(s.get('messages_count', 0) for s in sorted_sessions[:3])
        
        return max(message_growth / time_span, 0.1)  # Minimum velocity
    
    def _suggest_next_milestone(self, skills: List[SkillProgress], overall_score: float) -> str:
        """Suggest the next learning milestone"""
        if overall_score < 25:
            return "Complete foundational learning in your primary skill area"
        elif overall_score < 50:
            return "Achieve intermediate proficiency in two core competencies"
        elif overall_score < 75:
            return "Develop advanced skills and start specialization"
        else:
            return "Pursue expert-level mastery and leadership opportunities"
    
    def _estimate_completion_time(self, velocity: float, current_score: float) -> Optional[str]:
        """Estimate time to reach next major milestone"""
        try:
            remaining_score = 100 - current_score
            if remaining_score <= 10:
                return "You're near completion!"
            
            # Estimate based on current velocity
            estimated_days = remaining_score / max(velocity, 0.1)
            
            if estimated_days < 30:
                return f"Approximately {int(estimated_days)} days"
            elif estimated_days < 365:
                return f"Approximately {int(estimated_days/30)} months"
            else:
                return f"Approximately {int(estimated_days/365)} years"
                
        except:
            return "Progress continues with consistent effort"
    
    def _create_fallback_analysis(self, candidate_id: str) -> ProgressAnalysis:
        """Create basic analysis when AI analysis fails"""
        return ProgressAnalysis(
            candidate_id=candidate_id,
            overall_progress_score=30.0,
            learning_velocity=1.0,
            engagement_level="medium",
            primary_learning_style=LearningStyle.ANALYTICAL,
            skill_assessments=[],
            key_insights=[
                LearningInsight(
                    insight_type="opportunity",
                    title="Getting Started",
                    description="Continue engaging with the platform to build your learning profile",
                    confidence=0.5,
                    agent_source="guru",
                    suggested_actions=["Complete more sessions to enable AI analysis"]
                )
            ],
            guru_recommendations=["Establish a regular learning routine", "Focus on one skill area initially"],
            parikshak_recommendations=["Start with basic interview preparation", "Practice communication skills"],
            next_milestone="Build foundational skills through consistent practice",
            estimated_completion_time="Progress depends on consistency"
        )

# Global AI intelligence instance
ai_progress = AIProgressIntelligence()