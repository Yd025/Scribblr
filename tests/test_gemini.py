"""
Test Gemini summarization with a hardcoded or custom transcript.
Shows what Gemini would tell the machine to write on the board.

Usage:
    python -m tests.test_gemini
    python -m tests.test_gemini --text "Today we discuss eigenvalues and eigenvectors"
"""

import argparse

from python import config
from python.gemini_api import summarize

SAMPLE_TRANSCRIPTS = [
    # Chunk 1: Intro with filler and repetition
    (
        "Today we will be talking about linear algebra specifically eigenvalues. "
        "I know that many of you are mot familiar with the concept of eigenvalue "
        "and have neber jeard about this word befpre. Therefore we can take a step "
        "nack and think about what we know about vectors and span. So just to "
        "remind you, a vector is basically a quantity that has both magnitude and "
        "direction right, and we talked about this last week so I won't go into "
        "too much detail on that."
    ),
    # Chunk 2: Professor rambling with filler, then introducing a real concept
    (
        "OK so uh let me just pull up the slides here. So as I was saying, "
        "um the reason why eigenvalues are so important is because they show up "
        "everywhere in engineering and physics and computer science. Like if you "
        "think about Google's PageRank algorithm, that's literally just finding "
        "the dominant eigenvector of a matrix. But anyway let me not get ahead "
        "of myself. So the identity matrix, does everyone remember what the "
        "identity matrix is? It's the matrix with ones on the diagonal and zeros "
        "everywhere else. When you multiply any matrix by the identity matrix "
        "you get the same matrix back. OK so that's just a quick review."
    ),
    # Chunk 3: Pure filler / no new concept — should return NONE
    (
        "Does anyone have any questions so far? No? OK good. Let me take a sip "
        "of water. Alright so uh where were we. Right so we were talking about "
        "eigenvalues. Let me just check if the projector is working properly. "
        "Can everyone in the back see this? OK great."
    ),
    # Chunk 4: Actual new concept being introduced with messy speech
    (
        "So here's the key idea. If you have a matrix A and you multiply it by "
        "some vector v and you get back lambda times v, so A times v equals "
        "lambda v, then we say that v is an eigenvector of A and lambda is the "
        "corresponding eigenvalue. And the word eigen actually comes from German "
        "it means like self or own. So an eigenvector is like the vector that "
        "belongs to that transformation if that makes sense."
    ),
    # Chunk 5: Another concept with STT errors
    (
        "Now to actually find the eigenvalues what we do is we take the "
        "determinant of A minus lambda I and we set that equal to zero. And "
        "that gives us whats called the characteristic equation or sometimes "
        "people call it the characteristik polynomial. And the roots of that "
        "polynomial are your eigenvalues. So for a two by two matrix you'd get "
        "a quadratic and for a three by three you'd get a cubic and so on. "
        "Let me write that on the board. So det of A minus lambda I equals zero."
    ),
]


def main():
    parser = argparse.ArgumentParser(description="Test Gemini summarization")
    parser.add_argument("--text", type=str, default=None, help="Custom transcript text")
    args = parser.parse_args()

    print(f"Board config: {config.MAX_CHARS_PER_LINE} chars/line, {config.MAX_LINES} lines\n")

    transcripts = [args.text] if args.text else SAMPLE_TRANSCRIPTS
    written_history: list[str] = []

    for i, transcript in enumerate(transcripts, 1):
        print(f"── Transcript {i} ─────────────────────────────────")
        print(transcript)
        print()

        lines_remaining = config.MAX_LINES - len(written_history)
        result = summarize(transcript, written_history, lines_remaining)

        print(f"── Gemini says to write ────────────────────────────")
        if result is None:
            print("(NONE — nothing worth writing)")
        else:
            print(result)
            for line in result.splitlines():
                written_history.append(line.strip())
        print()

    print(f"── Full board state ────────────────────────────────")
    for line in written_history:
        print(f"  | {line}")
    print()


if __name__ == "__main__":
    main()
