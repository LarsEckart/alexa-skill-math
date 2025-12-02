"""
German language data and prompts for the Math Quiz Alexa Skill.

This module contains all German text strings used by the skill,
including welcome messages, feedback, help text, and speech patterns.
"""

# Skill metadata
SKILL_TITLE = "Mathe-Quiz für Grundschüler"

# Maximum questions per quiz session
MAX_QUESTIONS = 10

# ============================================================================
# Welcome and Launch Messages
# ============================================================================

WELCOME_MESSAGE = "Hallo! Willkommen beim Mathe-Quiz! Wer spielt heute?"

WELCOME_MESSAGE_RETURNING = (
    "Hallo {name}! Schön, dass du wieder da bist. "
    "Beim letzten Mal hattest du {correct} von {total} richtig. "
    "Möchtest du wieder üben?"
)

WELCOME_MESSAGE_RETURNING_NO_STATS = (
    "Hallo {name}! Schön, dass du wieder da bist. Möchtest du rechnen üben?"
)

WELCOME_MESSAGE_NEW_PLAYER = (
    "Hallo {name}! Schön dich kennenzulernen. In welche Klasse gehst du? Erste bis vierte?"
)

# ============================================================================
# Setup Flow Messages
# ============================================================================

ASK_PLAYER = "Wer spielt heute?"

ASK_GRADE = "In welche Klasse gehst du, {name}? Erste bis vierte?"

CONFIRM_GRADE = "Prima! Du bist also in der {grade}. Klasse. Lass uns anfangen!"

INVALID_GRADE = "Ich trainiere Mathe für die erste bis vierte Klasse. In welche Klasse gehst du?"

# ============================================================================
# Quiz Messages
# ============================================================================

START_QUIZ_MESSAGE = "Lass uns rechnen! Hier kommt die erste Aufgabe: "

NEXT_QUESTION = "Nächste Aufgabe: "

QUESTION_NUMBER = "Aufgabe {number}: "

# ============================================================================
# Answer Feedback - Correct
# ============================================================================

# German speech interjections for correct answers
CORRECT_SPEECHCONS = [
    "Super",
    "Prima",
    "Toll",
    "Klasse",
    "Wunderbar",
    "Ausgezeichnet",
    "Fantastisch",
    "Spitze",
    "Sehr gut",
    "Richtig",
    "Genau",
    "Bravo",
    "Jawohl",
]

CORRECT_ANSWER_TEMPLATES = [
    "Super! Das ist richtig!",
    "Prima! {answer} ist die richtige Antwort!",
    "Toll gemacht! {answer} stimmt!",
    "Genau richtig!",
    "Spitze! Das war richtig!",
    "Sehr gut!",
    "Klasse! {answer} ist korrekt!",
]

# ============================================================================
# Answer Feedback - Incorrect
# ============================================================================

# German speech interjections for incorrect answers
WRONG_SPEECHCONS = [
    "Oh",
    "Hmm",
    "Schade",
    "Ups",
    "Oh nein",
]

WRONG_ANSWER_TEMPLATES = [
    "Hmm, das war leider falsch. {operand1} {operation} {operand2} ist {answer}.",
    "Schade, das stimmt nicht. Die richtige Antwort ist {answer}.",
    "Das war leider nicht richtig. {operand1} {operation} {operand2} ergibt {answer}.",
    "Nicht ganz. Die Antwort ist {answer}.",
]

# ============================================================================
# Quiz End Messages
# ============================================================================

QUIZ_END_PERFECT = (
    "Wow! Du hast alle {total} Aufgaben richtig! Das war perfekt! "
    "Du bist ein echter Mathe-Champion!"
)

QUIZ_END_GREAT = (
    "Super gemacht! Du hattest {correct} von {total} richtig. Das ist ein tolles Ergebnis!"
)

QUIZ_END_GOOD = "Gut gemacht! Du hattest {correct} von {total} richtig. Weiter so!"

QUIZ_END_KEEP_PRACTICING = (
    "Du hattest {correct} von {total} richtig. "
    "Das wird bestimmt besser mit mehr Übung! "
    "Möchtest du noch einmal spielen?"
)

# ============================================================================
# Progress and Statistics
# ============================================================================

PROGRESS_REPORT = (
    "Du hast insgesamt {total} Aufgaben beantwortet. "
    "Davon waren {correct} richtig, das sind {percentage} Prozent. "
)

PROGRESS_STREAK = "Deine längste Serie richtiger Antworten war {streak}. "

PROGRESS_STRONG_AREAS = "Du bist super bei {areas}! "

PROGRESS_WEAK_AREAS = "{areas} musst du noch üben. "

PROGRESS_NO_DATA = (
    "Du hast noch keine Aufgaben beantwortet. Sag einfach 'Quiz starten' um loszulegen!"
)

# ============================================================================
# Difficulty and Grade
# ============================================================================

DIFFICULTY_CHANGED = "Alles klar! Ich stelle die Aufgaben jetzt auf Klasse {grade} um."

DIFFICULTY_EASIER = "Okay, ich mache die Aufgaben etwas leichter."

DIFFICULTY_HARDER = "Gut, ich mache die Aufgaben etwas schwieriger."

DIFFICULTY_SAME = "Du bist schon auf dem {direction} Level."

# ============================================================================
# Help Messages
# ============================================================================

HELP_MESSAGE = (
    "Ich kann dir helfen, Mathe zu üben. "
    "Sag 'Quiz starten' um zu rechnen, "
    "'Wie gut bin ich' für deine Fortschritte, "
    "oder 'Mach es leichter' oder 'schwerer' um die Schwierigkeit anzupassen. "
    "Was möchtest du tun?"
)

HELP_DURING_QUIZ = (
    "Sag mir einfach die Antwort als Zahl. "
    "Wenn du die Aufgabe nochmal hören willst, sag 'Wiederhole'. "
    "Zum Beenden sag 'Stopp'."
)

# ============================================================================
# Repeat and Reprompt
# ============================================================================

REPEAT_QUESTION = "Noch einmal: {question}"

REPROMPT_QUIZ = "Was ist die Antwort?"

REPROMPT_GENERAL = "Möchtest du rechnen üben? Sag einfach 'Quiz starten'."

# ============================================================================
# Exit Messages
# ============================================================================

EXIT_SKILL_MESSAGE = "Tschüss! Bis zum nächsten Mal beim Mathe-Quiz!"

EXIT_DURING_QUIZ = (
    "Okay, wir hören auf. Du hattest {correct} von {answered} richtig. Bis zum nächsten Mal!"
)

EXIT_SAVE_PROGRESS = "Ich habe deinen Fortschritt gespeichert. Bis bald!"

# ============================================================================
# Error Messages
# ============================================================================

FALLBACK_MESSAGE = "Das habe ich leider nicht verstanden. Sag 'Hilfe' wenn du nicht weiter weißt."

ERROR_MESSAGE = "Es tut mir leid, da ist etwas schiefgegangen. Bitte versuche es noch einmal."

NOT_UNDERSTOOD_DURING_QUIZ = (
    "Ich habe die Zahl nicht verstanden. Bitte sag mir nur die Antwort als Zahl."
)

# ============================================================================
# Operation words for German speech
# ============================================================================

OPERATION_WORDS = {
    "add": "plus",
    "sub": "minus",
    "mul": "mal",
    "div": "geteilt durch",
}

# German names for operations (for progress reports)
OPERATION_NAMES = {
    "add": "Addition",
    "sub": "Subtraktion",
    "mul": "Multiplikation",
    "div": "Division",
}

OPERATION_NAMES_FRIENDLY = {
    "add": "Plus-Aufgaben",
    "sub": "Minus-Aufgaben",
    "mul": "Mal-Aufgaben",
    "div": "Geteilt-Aufgaben",
}

# ============================================================================
# Session States
# ============================================================================

STATE_NONE = "NONE"
STATE_ASK_PLAYER = "ASK_PLAYER"
STATE_SETUP_GRADE = "SETUP_GRADE"
STATE_QUIZ = "QUIZ"

# ============================================================================
# Grade level names
# ============================================================================

GRADE_NAMES = {
    1: "erste",
    2: "zweite",
    3: "dritte",
    4: "vierte",
}
