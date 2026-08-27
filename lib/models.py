import os
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class CharacterMetadata(BaseModel):
    name: str
    gender: str | None = None
    birth_year: int | None = None
    age: int | None = None
    hair: str | None = None
    facial_hair: str | None = None
    eyes: str | None = None
    face_structure: str | None = None
    visual_look: str | None = None
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)
    raw_data: dict = Field(default_factory=dict)
    synthetic: bool = False  # True for AI-generated test characters

    @classmethod
    def from_yaml_dict(cls, data: dict) -> 'CharacterMetadata':
        """Parse character metadata from various YAML schemas (modern/legacy)."""
        name = data.get("name", "Unknown")
        gender = data.get("gender")
        birth_year = data.get("birth_year") or (data.get("dob", "").split("-")[0] if isinstance(data.get("dob"), str) else None)
        
        # Extract reality/appearance
        reality = data.get("reality", {}) or {}
        aspirational = data.get("aspirational", {}) or {}
        appearance = data.get("appearance", {}) or {}
        
        hair = aspirational.get("hair") or appearance.get("hair") or reality.get("hair") or data.get("hair_color")
        facial_hair = aspirational.get("facial_hair") or appearance.get("facial_hair") or reality.get("facial_hair")
        eyes = appearance.get("eyes") or reality.get("eyes") or data.get("eye_color")
        face_struct = appearance.get("face_structure") or reality.get("face_structure")
        visual_look = reality.get("visual_look") or data.get("description")
        
        # Must include & must avoid
        must_inc = list(data.get("prompt_guidelines", {}).get("must_include", []))
        must_inc.extend(aspirational.get("prompt_anchors", []))
        
        must_av = list(data.get("prompt_guidelines", {}).get("must_avoid", []))
        must_av.extend(data.get("wardrobe", {}).get("must_avoid", []))
        must_av.extend(aspirational.get("must_avoid", []))
        
        return cls(
            name=name,
            gender=gender,
            birth_year=int(birth_year) if birth_year and str(birth_year).isdigit() else None,
            hair=hair,
            facial_hair=facial_hair,
            eyes=eyes,
            face_structure=face_struct,
            visual_look=visual_look,
            must_include=must_inc,
            must_avoid=must_av,
            raw_data=data,
            synthetic=data.get("synthetic", False),
        )

    def to_biometric_blueprint(self) -> str:
        """Format character profile as positive biometric instructions."""
        parts = []
        if self.visual_look:
            parts.append(self.visual_look)
        if self.hair:
            parts.append(f"Hair: {self.hair}")
        if self.facial_hair:
            parts.append(f"Facial hair: {self.facial_hair}")
        if self.eyes:
            parts.append(f"Eyes: {self.eyes}")
        if self.face_structure:
            parts.append(f"Facial structure: {self.face_structure}")
        if self.must_include:
            parts.extend(self.must_include)
        return ". ".join(parts)

class JudgeVerdict(BaseModel):
    facial_similarity: float = Field(..., ge=0.0, le=10.0, description="How similar the face looks to reference photos (identity only, NOT clothing)")
    scene_adaptation: float = Field(..., ge=0.0, le=10.0, description="How well clothing/pose/setting match the PROMPT (not the reference photos)")
    adherence_score: float = Field(..., ge=0.0, le=10.0, description="How well the scene matches the prompt")
    is_photorealistic: bool = Field(..., description="True if the image looks photorealistic, not cartoon/illustration")
    facial_similarity_rationale: str = Field(..., description="Why this facial similarity score was given")
    scene_adaptation_rationale: str = Field(..., description="Why this scene adaptation score was given")
    adherence_rationale: str = Field(..., description="Why this adherence score was given")
    character_facial_scores: list[float] = Field(default_factory=list, description="Facial similarity scores for each character: [F1, F2, ...]")
    character_facial_rationales: list[str] = Field(default_factory=list, description="Facial rationales for each character")
    anti_beautification_flag: bool = Field(default=False, description="True if AI smoothing/beautification was detected")
    verdict_label: str = Field(default="", description="Italian label: CAPOLAVORO/BUONO/COSÌ-COSÌ/SCHIFO")
    
    @property
    def average_score(self) -> float:
        """Calculate the arithmetic mean (MEDIA) of all evaluated axes."""
        scores = self.character_facial_scores if self.character_facial_scores else [self.facial_similarity]
        all_axes = [*scores, self.scene_adaptation, self.adherence_score]
        return sum(all_axes) / len(all_axes) if all_axes else 0.0

    @property
    def bottleneck_score(self) -> float:
        """Calculate the bottleneck (minimum) score across all axes."""
        scores = self.character_facial_scores if self.character_facial_scores else [self.facial_similarity]
        return min([*scores, self.scene_adaptation, self.adherence_score])

    @model_validator(mode='before')
    @classmethod
    def handle_legacy_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            # Map legacy resemblance_score -> facial_similarity
            if "facial_similarity" not in data and "resemblance_score" in data:
                data["facial_similarity"] = data["resemblance_score"]
            if "facial_similarity_rationale" not in data and "resemblance_rationale" in data:
                data["facial_similarity_rationale"] = data["resemblance_rationale"]
            if "scene_adaptation" not in data:
                data["scene_adaptation"] = data.get("adherence_score", 7.0)
            if "scene_adaptation_rationale" not in data:
                data["scene_adaptation_rationale"] = data.get("adherence_rationale", "")
            if "is_photorealistic" not in data:
                data["is_photorealistic"] = True
            if "character_facial_scores" in data and data["character_facial_scores"]:
                if "facial_similarity" not in data or data["facial_similarity"] == 0.0:
                    data["facial_similarity"] = min(data["character_facial_scores"])
        return data

    @model_validator(mode='after')
    def set_verdict_label(self) -> 'JudgeVerdict':
        """Set Italian verdict label based on minimum of all facial similarities and adherence."""
        min_facial = min(self.character_facial_scores) if self.character_facial_scores else self.facial_similarity
        min_score = min(min_facial, self.adherence_score)
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
    character: str = ""
    characters: list[str] = Field(default_factory=list)
    ref_dir: str = Field(default_factory=lambda: os.getenv("PORTR8_REF_DIR", "data/characters"))
    image_model: str = Field(default_factory=lambda: os.getenv("PORTR8_IMAGE_MODEL", "gemini-3.1-flash-image-preview"))
    judge_model: str = Field(default_factory=lambda: os.getenv("PORTR8_JUDGE_MODEL", "gemini-3.5-flash"))
    target_score: float = Field(default_factory=lambda: float(os.getenv("PORTR8_TARGET_SCORE", "8.0")))
    max_iterations: int = Field(default_factory=lambda: int(os.getenv("PORTR8_MAX_ITERATIONS", "20")))
    dual_strategy: bool = False
    no_edit: bool = False  # When True, always regenerate — never pass previous image
    seed: int | None = None
    ref_transport: str = Field(default_factory=lambda: os.getenv("PORTR8_REF_TRANSPORT", "files_api"))
    image_type: Literal["photo", "cartoon", "illustration"] = "photo"
    portr8_version: str = "0.1.0"

    @model_validator(mode='after')
    def sync_character_lists(self) -> 'RunConfig':
        """Ensure characters and character stay in sync."""
        if not self.characters and self.character:
            self.characters = [c.strip() for c in self.character.split(",") if c.strip()]
        elif self.characters and not self.character:
            self.character = ", ".join(self.characters)
        return self

class RunSummary(BaseModel):
    config: RunConfig
    iterations: list[IterationRecord]
    best_iteration: int  # index of best iteration
    best_facial_similarity: float
    best_scene_adaptation: float
    best_adherence: float
    best_character_facial_scores: list[float] = Field(default_factory=list)
    converged: bool  # True if all facial_similarities & adherence >= target AND scene_adaptation >= 5.0
    total_elapsed: float
    output_dir: str  # tilde-normalized path
    best_image_path: str = ""  # path to best scored image
    graph_path: str = ""  # path to convergence graph PNG

    @model_validator(mode='before')
    @classmethod
    def handle_legacy_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            if "best_facial_similarity" not in data and "best_resemblance" in data:
                data["best_facial_similarity"] = data["best_resemblance"]
            if "best_scene_adaptation" not in data:
                data["best_scene_adaptation"] = data.get("best_adherence", 7.0)
        return data
