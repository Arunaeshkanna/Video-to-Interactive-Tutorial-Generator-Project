from __future__ import annotations

import json

from src.config import AppConfig
from src.llm import LLMClient
from src.models import Diagram, KeyFrame, TutorialResult
from src.rag import TranscriptRAG


class TutorialCrew:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.llm = LLMClient(config)
        self.crewai_llm = None
        self._crewai = None

        try:
            from crewai import Agent, Crew, LLM, Task

            self.crewai_llm = LLM(
                model=f"groq/{config.groq_model}",
                api_key=config.groq_api_key,
                temperature=0.35,
            )
            self._crewai = (Agent, Crew, Task)
        except Exception:
            self.crewai_llm = None
            self._crewai = None

    def run(self, title: str, transcript: str, frames: list[KeyFrame], tone: str) -> TutorialResult:
        clipped = transcript[: self.config.max_transcript_chars]
        rag = TranscriptRAG.from_text(clipped)
        context = rag.retrieve("core technical concepts architecture implementation steps pitfalls", top_k=6)

        if self._crewai and self.crewai_llm:
            analysis = self._analysis_with_crewai(title, clipped, context)
            blog = self._writer_with_crewai(title, tone, analysis, context, frames)
            diagrams = self._diagram_with_crewai(title, analysis, context)
            checkpoints = self._coach_with_crewai(analysis, context)
        else:
            analysis = self._analysis_agent(title, clipped, context)
            blog = self._writer_agent(title, tone, analysis, context, frames)
            diagrams = self._diagram_agent(title, analysis, context)
            checkpoints = self._coach_agent(analysis, context)

        analysis = analysis or self._analysis_agent(title, clipped, context)
        blog = blog or self._writer_agent(title, tone, analysis, context, frames)
        diagrams = diagrams or self._diagram_agent(title, analysis, context)
        checkpoints = checkpoints or self._coach_agent(analysis, context)

        return TutorialResult(
            summary=analysis,
            blog=blog,
            diagrams=diagrams,
            checkpoints=checkpoints,
            retrieved_context=context,
        )

    def _analysis_with_crewai(self, title: str, transcript: str, context: list[str]) -> str:
        prompt = f"""
Title: {title}

RAG context:
{chr(10).join(context)}

Transcript:
{transcript}

Extract the main learning objective, prerequisites, major sections, concepts, commands/APIs, and likely pain points.
"""
        result = self._run_crewai_step(
            role="Technical Curriculum Analyst",
            goal="Turn the transcript into a structured tutorial analysis.",
            backstory="You are a senior technical curriculum analyst who turns dense video content into clear study material.",
            prompt=prompt,
            expected_output="A concise but practical analysis with learning objectives, prerequisites, concepts, commands/APIs, and pain points.",
        )
        return result or self._analysis_agent(title, transcript, context)

    def _writer_with_crewai(self, title: str, tone: str, analysis: str, context: list[str], frames: list[KeyFrame]) -> str:
        frame_notes = "\n".join(f"- {frame.timestamp_label}: {frame.caption}" for frame in frames)
        prompt = f"""
Write a complete {tone.lower()} tutorial as Markdown.

Title: {title}
Analysis:
{analysis}

Relevant transcript evidence:
{chr(10).join(context)}

Key frames:
{frame_notes}

Include: overview, learning goals, prerequisites, step-by-step explanation, key frame callouts, common mistakes, recap, and next steps.
Do not mention hidden API keys or environment values.
"""
        result = self._run_crewai_step(
            role="Tutorial Writer",
            goal="Write a polished tutorial from the analysis and transcript evidence.",
            backstory="You transform technical videos into readable engineering tutorials with clear structure and examples.",
            prompt=prompt,
            expected_output="A complete Markdown tutorial with headings, steps, key frame notes, and recap.",
        )
        return result or self._writer_agent(title, tone, analysis, context, frames)

    def _diagram_with_crewai(self, title: str, analysis: str, context: list[str]) -> list[Diagram]:
        prompt = f"""
Create exactly two Mermaid diagrams for this tutorial.
Return JSON only with this shape:
{{"diagrams":[{{"title":"...", "code":"graph TD\\nA[Start] --> B[Next]"}}]}}

Title: {title}
Analysis:
{analysis}

Context:
{chr(10).join(context)}
"""
        result = self._run_crewai_step(
            role="Mermaid Designer",
            goal="Generate clean Mermaid diagrams for the tutorial.",
            backstory="You design clear Mermaid diagrams that teach technical ideas visually.",
            prompt=prompt,
            expected_output="Valid JSON with two diagrams and their titles and Mermaid code.",
        )
        if result:
            return self._parse_diagrams(result)
        return self._diagram_agent(title, analysis, context)

    def _coach_with_crewai(self, analysis: str, context: list[str]) -> list[dict[str, str]]:
        prompt = f"""
Create five short self-check questions and answers for a learner.
Return JSON only with this shape:
{{"checkpoints":[{{"question":"...", "answer":"..."}}]}}

Analysis:
{analysis}

Context:
{chr(10).join(context)}
"""
        result = self._run_crewai_step(
            role="Learning Coach",
            goal="Create practical review checkpoints for the tutorial.",
            backstory="You create concise learner checkpoints that help students verify understanding.",
            prompt=prompt,
            expected_output="Valid JSON with five self-check questions and answers.",
        )
        if result:
            return self._parse_checkpoints(result)
        return self._coach_agent(analysis, context)

    def _run_crewai_step(self, role: str, goal: str, backstory: str, prompt: str, expected_output: str) -> str:
        if not self._crewai or not self.crewai_llm:
            return ""
        Agent, Crew, Task = self._crewai
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=self.crewai_llm,
            allow_delegation=False,
            verbose=False,
        )
        task = Task(description=prompt, expected_output=expected_output, agent=agent)
        try:
            output = Crew(agents=[agent], tasks=[task], verbose=False, tracing=False).kickoff()
            return str(getattr(output, "raw", output)).strip()
        except Exception:
            return ""

    def _parse_diagrams(self, raw: str) -> list[Diagram]:
        try:
            data = json.loads(raw.strip()) if raw.strip().startswith("{") else json.loads(raw.strip("` ").replace("json", "", 1))
        except Exception:
            return []
        diagrams = []
        for item in data.get("diagrams", [])[:2]:
            title_value = str(item.get("title", "Tutorial flow")).strip()
            code = str(item.get("code", "")).strip()
            if code:
                diagrams.append(Diagram(title=title_value, code=code))
        return diagrams

    def _parse_checkpoints(self, raw: str) -> list[dict[str, str]]:
        try:
            data = json.loads(raw.strip()) if raw.strip().startswith("{") else json.loads(raw.strip("` ").replace("json", "", 1))
        except Exception:
            return []
        checkpoints = []
        for item in data.get("checkpoints", [])[:5]:
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                checkpoints.append({"question": question, "answer": answer})
        return checkpoints

    def _analysis_agent(self, title: str, transcript: str, context: list[str]) -> str:
        prompt = f"""
Title: {title}

RAG context:
{chr(10).join(context)}

Transcript:
{transcript}

Extract the main learning objective, prerequisites, major sections, concepts, commands/APIs, and likely pain points.
"""
        response = self.llm.complete(
            "You are a senior technical curriculum analyst. Be precise, structured, and practical.",
            prompt,
        )
        if response:
            return response
        return self._fallback_analysis(title, transcript)

    def _writer_agent(
        self,
        title: str,
        tone: str,
        analysis: str,
        context: list[str],
        frames: list[KeyFrame],
    ) -> str:
        frame_notes = "\n".join(f"- {frame.timestamp_label}: {frame.caption}" for frame in frames)
        prompt = f"""
Write a complete {tone.lower()} tutorial as Markdown.

Title: {title}
Analysis:
{analysis}

Relevant transcript evidence:
{chr(10).join(context)}

Key frames:
{frame_notes}

Include: overview, learning goals, prerequisites, step-by-step explanation, key frame callouts, common mistakes, recap, and next steps.
Do not mention hidden API keys or environment values.
"""
        response = self.llm.complete(
            "You transform technical videos into accurate, readable engineering tutorials.",
            prompt,
        )
        if response:
            return response
        return self._fallback_blog(title, analysis, context, frames)

    def _diagram_agent(self, title: str, analysis: str, context: list[str]) -> list[Diagram]:
        prompt = f"""
Create exactly two Mermaid diagrams for this tutorial.
Return JSON only with this shape:
{{"diagrams":[{{"title":"...", "code":"graph TD\\nA[Start] --> B[Next]"}}]}}

Title: {title}
Analysis:
{analysis}

Context:
{chr(10).join(context)}
"""
        data = self.llm.complete_json(
            "You design clear Mermaid diagrams for technical teaching. Return valid JSON only.",
            prompt,
        )
        diagrams = []
        for item in data.get("diagrams", [])[:2]:
            title_value = str(item.get("title", "Tutorial flow")).strip()
            code = str(item.get("code", "")).strip()
            if code:
                diagrams.append(Diagram(title=title_value, code=code))
        if diagrams:
            return diagrams
        return [
            Diagram(
                title="Tutorial learning flow",
                code="graph TD\nA[Watch video] --> B[Extract transcript]\nB --> C[Identify key concepts]\nC --> D[Follow implementation steps]\nD --> E[Practice and review]",
            ),
            Diagram(
                title="Generator architecture",
                code="flowchart LR\nV[Video or YouTube URL] --> T[Transcript Agent]\nV --> F[Frame Agent]\nT --> R[RAG Retriever]\nR --> W[Writer Agent]\nF --> W\nW --> O[Interactive Tutorial]",
            ),
        ]

    def _coach_agent(self, analysis: str, context: list[str]) -> list[dict[str, str]]:
        prompt = f"""
Create five short self-check questions and answers for a learner.
Return JSON only with this shape:
{{"checkpoints":[{{"question":"...", "answer":"..."}}]}}

Analysis:
{analysis}

Context:
{chr(10).join(context)}
"""
        data = self.llm.complete_json(
            "You create practical learner checkpoints. Return valid JSON only.",
            prompt,
        )
        checkpoints = []
        for item in data.get("checkpoints", [])[:5]:
            question = str(item.get("question", "")).strip()
            answer = str(item.get("answer", "")).strip()
            if question and answer:
                checkpoints.append({"question": question, "answer": answer})
        if checkpoints:
            return checkpoints
        return [
            {"question": "What problem is this video trying to solve?", "answer": "Identify the main task from the tutorial overview and map each section back to that goal."},
            {"question": "Which concepts should you understand before coding?", "answer": "Review the prerequisites and the first key concepts extracted from the transcript."},
            {"question": "Where are mistakes most likely?", "answer": "Focus on setup, dependency versions, API configuration, and any step that changes application state."},
        ]

    def _fallback_analysis(self, title: str, transcript: str) -> str:
        preview = transcript[:1400]
        return (
            f"Tutorial topic: {title}\n\n"
            "Main objective: convert the video content into a practical learning path.\n\n"
            "Detected transcript preview:\n"
            f"{preview}\n\n"
            "Use the transcript sections as the source of truth for implementation steps, definitions, and recap notes."
        )

    def _fallback_blog(self, title: str, analysis: str, context: list[str], frames: list[KeyFrame]) -> str:
        frame_lines = "\n".join(f"- **{frame.timestamp_label}**: {frame.caption}" for frame in frames) or "- No frames available."
        context_lines = "\n".join(f"- {item}" for item in context[:5]) or "- Transcript context was limited."
        return f"""# {title}

## Overview

This tutorial was generated from the available transcript and video frames. It organizes the lesson into a clean learning path you can read, review, and export.

## Learning Goals

- Understand the core objective of the video.
- Follow the implementation or explanation in a structured order.
- Review the important visual moments from the recording.
- Practice with self-check questions.

## Extracted Analysis

{analysis}

## RAG Highlights

{context_lines}

## Key Frame Callouts

{frame_lines}

## Step-by-Step Tutorial

1. Start with the main problem introduced in the video.
2. Identify the prerequisites and tools used by the presenter.
3. Follow each concept in sequence using the transcript highlights.
4. Pause at key frames to connect the explanation with the visual state.
5. Rebuild the final workflow in your own environment.

## Common Mistakes

- Skipping setup steps before running the main workflow.
- Copying commands without checking paths, versions, or environment variables.
- Missing the relationship between the visual demo and the spoken explanation.

## Recap

The video has been transformed into a structured tutorial with transcript-backed notes, visual callouts, diagrams, and review checkpoints.
"""
