"""
Firestore Service - Database operations for analysis storage and user management
Handles storing analysis results, user data, and trial tracking
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from google.cloud import firestore


class FirestoreService:
    """Service for managing Firestore operations"""

    def __init__(self):
        """Initialize Firestore client"""
        self.client = None
        self.enabled = False

        try:
            # Initialize Firestore client
            # Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS env var
            self.client = firestore.Client()
            self.enabled = True
            print("[Firestore] Initialized successfully")
        except Exception as e:
            print(f"[Firestore] Initialization failed: {e}. Database features disabled.")
            self.enabled = False

    # ==================== Analysis Operations ====================

    def save_analysis(
        self,
        user_id: Optional[str],
        analysis_result: Dict[str, Any],
        file_names: List[str]
    ) -> Optional[str]:
        """
        Save analysis result to Firestore

        Args:
            user_id: User ID (None for anonymous/trial users)
            analysis_result: Complete analysis result from orchestrator
            file_names: List of uploaded file names

        Returns:
            Analysis document ID or None if save failed
        """
        if not self.enabled:
            print("[Firestore] Cannot save analysis - Firestore not enabled")
            return None

        try:
            # Prepare analysis document
            analysis_doc = {
                "user_id": user_id or "anonymous",
                "created_at": firestore.SERVER_TIMESTAMP,
                "file_names": file_names,
                "cohort": analysis_result.get("cohort", {}),
                "score": analysis_result.get("score", {}),
                "verdict": analysis_result.get("score", {}).get("verdict", "N/A"),
                "executive_summary": analysis_result.get("executiveSummary", ""),
                "market_analysis": analysis_result.get("marketAnalysis", {}),
                "risks": analysis_result.get("risks", []),
                "recommendations": analysis_result.get("recommendations", []),
                "extracted_metrics": analysis_result.get("extractedMetrics", {}),
                "benchmarks": analysis_result.get("benchmarks", {}),
                "processing_info": analysis_result.get("processingInfo", {}),
                "llm_status": analysis_result.get("llmStatus", {})
            }

            # Add to Firestore
            doc_ref = self.client.collection("analyses").document()
            doc_ref.set(analysis_doc)

            analysis_id = doc_ref.id
            print(f"[Firestore] Analysis saved: {analysis_id}")

            # Update user's analysis count if user is authenticated
            if user_id and user_id != "anonymous":
                self._increment_user_analysis_count(user_id)

            return analysis_id

        except Exception as e:
            print(f"[Firestore] Error saving analysis: {e}")
            return None

    def get_analysis(self, analysis_id: str) -> Optional[Dict]:
        """Get a specific analysis by ID"""
        if not self.enabled:
            return None

        try:
            doc = self.client.collection("analyses").document(analysis_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"[Firestore] Error getting analysis: {e}")
            return None

    def get_user_analyses(
        self,
        user_id: str,
        limit: int = 10,
        order_by: str = "created_at"
    ) -> List[Dict]:
        """
        Get analysis history for a user

        Args:
            user_id: User ID
            limit: Maximum number of analyses to return
            order_by: Field to order by (default: created_at)

        Returns:
            List of analysis documents
        """
        if not self.enabled:
            return []

        try:
            query = (
                self.client.collection("analyses")
                .where("user_id", "==", user_id)
                .order_by(order_by, direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()
            analyses = []

            for doc in docs:
                analysis = doc.to_dict()
                analysis["id"] = doc.id
                analyses.append(analysis)

            print(f"[Firestore] Retrieved {len(analyses)} analyses for user {user_id}")
            return analyses

        except Exception as e:
            print(f"[Firestore] Error getting user analyses: {e}")
            return []

    # ==================== User Operations ====================

    def get_or_create_user(self, user_id: str, email: str, display_name: str = "") -> Dict:
        """
        Get user document or create if doesn't exist

        Args:
            user_id: Firebase user ID
            email: User email
            display_name: User display name

        Returns:
            User document
        """
        if not self.enabled:
            return {"user_id": user_id, "email": email, "trial_count": 0}

        try:
            user_ref = self.client.collection("users").document(user_id)
            user_doc = user_ref.get()

            if user_doc.exists:
                return user_doc.to_dict()

            # Create new user document
            new_user = {
                "user_id": user_id,
                "email": email,
                "display_name": display_name,
                "created_at": firestore.SERVER_TIMESTAMP,
                "subscription": "trial",
                "trial_count": 0,
                "analysis_count": 0,
                "last_active": firestore.SERVER_TIMESTAMP
            }

            user_ref.set(new_user)
            print(f"[Firestore] Created new user: {user_id}")
            return new_user

        except Exception as e:
            print(f"[Firestore] Error getting/creating user: {e}")
            return {"user_id": user_id, "email": email, "trial_count": 0}

    def _increment_user_analysis_count(self, user_id: str):
        """Increment user's analysis count"""
        try:
            user_ref = self.client.collection("users").document(user_id)
            user_ref.update({
                "analysis_count": firestore.Increment(1),
                "last_active": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"[Firestore] Error incrementing analysis count: {e}")

    # ==================== Trial Tracking ====================

    def track_trial_usage(self, ip_address: str, user_agent: str) -> Dict:
        """
        Track trial usage by IP address and user agent

        Args:
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Dict with trial_count and allowed status
        """
        if not self.enabled:
            return {"trial_count": 0, "allowed": True, "max_trials": 3}

        try:
            # Create unique ID from IP + User Agent hash
            import hashlib
            trial_id = hashlib.md5(f"{ip_address}:{user_agent}".encode()).hexdigest()

            trial_ref = self.client.collection("trials").document(trial_id)
            trial_doc = trial_ref.get()

            max_trials = 3
            cooldown_days = 7

            if trial_doc.exists:
                data = trial_doc.to_dict()
                trial_count = data.get("count", 0)
                last_used = data.get("last_used")

                # Check if cooldown period has passed
                if last_used and isinstance(last_used, datetime):
                    if datetime.now() - last_used > timedelta(days=cooldown_days):
                        # Reset trial count after cooldown
                        trial_count = 0

                # Increment count
                new_count = trial_count + 1
                trial_ref.update({
                    "count": new_count,
                    "last_used": firestore.SERVER_TIMESTAMP,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                })

                allowed = new_count <= max_trials

                print(f"[Firestore] Trial usage: {new_count}/{max_trials} (allowed={allowed})")
                return {
                    "trial_count": new_count,
                    "allowed": allowed,
                    "max_trials": max_trials
                }

            else:
                # First trial for this client
                trial_ref.set({
                    "count": 1,
                    "first_used": firestore.SERVER_TIMESTAMP,
                    "last_used": firestore.SERVER_TIMESTAMP,
                    "ip_address": ip_address,
                    "user_agent": user_agent
                })

                print(f"[Firestore] New trial user: 1/{max_trials}")
                return {
                    "trial_count": 1,
                    "allowed": True,
                    "max_trials": max_trials
                }

        except Exception as e:
            print(f"[Firestore] Error tracking trial usage: {e}")
            # On error, allow the request
            return {"trial_count": 0, "allowed": True, "max_trials": 3}

    # ==================== Benchmark Operations ====================

    def save_benchmark_data(self, sector: str, stage: str, metrics: Dict):
        """Save or update benchmark data for a cohort"""
        if not self.enabled:
            return

        try:
            cohort_id = f"{sector}_{stage}"
            benchmark_ref = self.client.collection("benchmarks").document(cohort_id)

            benchmark_ref.set({
                "sector": sector,
                "stage": stage,
                "metrics": metrics,
                "updated_at": firestore.SERVER_TIMESTAMP
            }, merge=True)

            print(f"[Firestore] Benchmark data saved: {cohort_id}")

        except Exception as e:
            print(f"[Firestore] Error saving benchmark data: {e}")

    def get_benchmark_data(self, sector: str, stage: str) -> Optional[Dict]:
        """Get benchmark data for a cohort"""
        if not self.enabled:
            return None

        try:
            cohort_id = f"{sector}_{stage}"
            doc = self.client.collection("benchmarks").document(cohort_id).get()

            if doc.exists:
                return doc.to_dict()
            return None

        except Exception as e:
            print(f"[Firestore] Error getting benchmark data: {e}")
            return None


# Global instance
_firestore_service = None

def get_firestore_service() -> FirestoreService:
    """Get or create the global FirestoreService instance"""
    global _firestore_service
    if _firestore_service is None:
        _firestore_service = FirestoreService()
    return _firestore_service
