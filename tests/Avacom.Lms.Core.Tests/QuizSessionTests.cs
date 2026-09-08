using Avacom.Lms.Core.Services;
namespace Avacom.Lms.Core.Tests;
public sealed class QuizSessionTests
{
    [Fact]
    public void DemoCourse_ContainsThreeSectionsAndSixItems()
    {
        Assert.Equal(3, DemoCatalog.Algebra.Sections.Count);
        Assert.Equal(6, DemoCatalog.Algebra.Sections.SelectMany(section => section.Lessons).SelectMany(lesson => lesson.Items).Count());
        Assert.Equal("Quiz", DemoCatalog.Algebra.Sections[^1].Lessons[^1].Items[^1].Kind);
    }

    [Fact]
    public void Finish_CalculatesSingleResultFromAnswers()
    {
        var session = new QuizSession(DemoCatalog.MexicoQuiz);
        foreach (var question in session.Questions)
        {
            session.Answer(question.CorrectOptionId);
            session.MoveNext();
        }
        var result = session.Finish();
        Assert.Equal(5, result.CorrectAnswers);
        Assert.Equal(100m, result.Score);
        Assert.Equal(24, result.AttemptId.Length);
    }

    [Fact]
    public void MoveNext_RequiresAnAnswer()
    {
        var session = new QuizSession(DemoCatalog.MexicoQuiz);
        Assert.False(session.MoveNext());
        Assert.Equal(0, session.CurrentIndex);
    }
}
