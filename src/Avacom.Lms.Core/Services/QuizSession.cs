using Avacom.Lms.Core.Models;

namespace Avacom.Lms.Core.Services;

public sealed class QuizSession(IReadOnlyList<QuizQuestion> questions)
{
    private readonly Dictionary<string, string> answers = [];
    public IReadOnlyList<QuizQuestion> Questions { get; } = questions;
    public int CurrentIndex { get; private set; }
    public QuizQuestion Current => Questions[CurrentIndex];
    public bool IsLast => CurrentIndex == Questions.Count - 1;

    public void Answer(string optionId) => answers[Current.Id] = optionId;

    public bool MoveNext()
    {
        if (!answers.ContainsKey(Current.Id)) return false;
        if (!IsLast) CurrentIndex++;
        return true;
    }

    public QuizResult Finish()
    {
        var correct = Questions.Count(question =>
            answers.TryGetValue(question.Id, out var answer) && answer == question.CorrectOptionId);
        var score = Questions.Count == 0 ? 0 : Math.Round((decimal)correct / Questions.Count * 100, 1);
        return new QuizResult(Guid.NewGuid().ToString("N")[..24], correct, Questions.Count, score);
    }
}
