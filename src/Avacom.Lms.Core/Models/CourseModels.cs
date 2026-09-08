namespace Avacom.Lms.Core.Models;

public sealed record LessonItem(string Id, string Title, string Kind, string Description, bool IsCompleted = false);

public sealed record Lesson(string Id, string Title, string Summary, IReadOnlyList<LessonItem> Items, int Progress = 0);

public sealed record CourseSection(string Id, string Title, string Subtitle, IReadOnlyList<Lesson> Lessons);

public sealed record Course(
    string Id,
    string Name,
    string Subject,
    string Grade,
    string Teacher,
    string Accent,
    IReadOnlyList<CourseSection> Sections,
    int Progress = 0);

public sealed record QuizOption(string Id, string Text);

public sealed record QuizQuestion(string Id, string Text, IReadOnlyList<QuizOption> Options, string CorrectOptionId);

public sealed record StudentProgress(
    string StudentId,
    string Name,
    string Initials,
    string Status,
    int CurrentQuestion,
    int TotalQuestions,
    decimal? Score = null);

public sealed record QuizResult(string AttemptId, int CorrectAnswers, int TotalQuestions, decimal Score);

