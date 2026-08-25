from typing import Literal
from pydantic import BaseModel, Field, model_validator

class CharacterMetadata(BaseModel):
    name: str
    age: int | None = None
    hair_color: str | None = None
    eye_color: str | None = None
    description: str | None = None
    synthetic: bool = False  # True for AI-generated test characters

class JudgeVerdict(BaseModel):
    facial_similarity: float = Field(..., ge=0.0, le=10.0, description="How similar the face looks to reference photos (identity only, NOT clothing)")
    scene_adaptation: float = Field(..., ge=0.0, le=10.0, description="How well clothing/pose/setting match the PROMPT (not the reference photos)")
    adherence_score: float = Field(..., ge=0.0, le=10.0, description="How well the scene matches the prompt")
    is_photorealistic: bool = Field(..., description="True if the image looks photorealistic, not cartoon/illustration")
    facial_similarity_rationale: str = Field(..., description="Why this facial similarity score was given")
    scene_adaptation_rationale: str = Field(..., description="Why this scene adaptation score was given")
    adherence_rationale: str = Field(..., description="Why this adherence score was given")
    anti_beautification_flag: bool = Field(default=False, description="True if AI smoothing/beautification was detected")
    verdict_label: str = Field(default="", description="Italian label: CAPOLAVORO/BUONO/COSÌ-COSÌ/SCHIFO")
    
    @model_validator(mode='after')
    def set_verdict_label(self) -> 'JudgeVerdict':
        """Set Italian verdict label based on minimum of facial_similarity and adherence."""
        min_score = min(self.facial_similarity, self.adherence_score)
        if min_score >= 8.0:
            self.verdict_label = "CAPOLAVORO 🏆"
        elif min_score >= 7.0:
            self.verdict_label = "BUONO 👍"
        elif min_score >= 5.0:
            self.verdict_label = "COSÌ-COSÌ 😐"
        else:
            self.verdict_label = "SCHIFO 🤮"
        return self

class StrategyDecision(BaseModel):
    strategy: Literal["regenerate", "edit"] = Field(..., description="Whether to regenerate from scratch or edit previous image")
    augmented_prompt: str = Field(..., description="The prompt after incorporating judge feedback")
    rationale: str = Field(..., description="Why this strategy was chosen")
    feedback_incorporated: list[str] = Field(default_factory=list, description="List of specific feedback points incorporated")

class IterationRecord(BaseModel):
    iteration: int
    timestamp: str  # ISO 8601
    image_path: str  # tilde-normalized path
    scored_image_path: str | None = None  # path to overlaid image
    original_prompt: str
    augmented_prompt: str
    strategy: Literal["regenerate", "edit", "initial"]
    seed: int | None = None
    image_model: str
    judge_model: str
    ref_transport: str = "files_api"
    verdict: JudgeVerdict
    strategy_decision: StrategyDecision | None = None  # None for iteration 0
    elapsed_seconds: float
    portr8_version: str

class RunConfig(BaseModel):
    prompt: str
    character: str
    ref_dir: str = "data/characters"
    image_model: str = "gemini-3.1-flash-image-preview"
    judge_model: str = "gemini-3.5-flash"
    target_score: float = 8.0
    max_iterations: int = 10
    dual_strategy: bool = False
    seed: int | None = None
    ref_transport: str = "files_api"
    image_type: Literal["photo", "cartoon", "illustration"] = "photo"
    portr8_version: str = "0.1.0"

class RunSummary(BaseModel):
    config: RunConfig
    iterations: list[IterationRecord]
    best_iteration: int  # index of best iteration
    best_facial_similarity: float
    best_scene_adaptation: float
    best_adherence: float
    converged: bool  # True if facial_similarity & adherence >= target AND scene_adaptation >= 5.0
    total_elapsed: float
    output_dir: str  # tilde-normalized path
    best_image_path: str = ""  # path to best scored image
    graph_path: str = ""  # path to convergence graph PNG
