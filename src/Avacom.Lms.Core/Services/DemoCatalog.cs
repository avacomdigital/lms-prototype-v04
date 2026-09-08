using Avacom.Lms.Core.Models;

namespace Avacom.Lms.Core.Services;

public static class DemoCatalog
{
    public static Course Algebra { get; } = new(
        "algebra-8b",
        "Álgebra Octavo B",
        "Matemáticas",
        "8° B",
        "Elena Castillo",
        "#E5262B",
        [
            new("section-1", "Unidad 1", "Lenguaje algebraico",
            [
                new("lesson-1", "Expresiones algebraicas", "Reconoce variables, constantes y términos.",
                [
                    new("item-1", "Variables y constantes", "Lectura", "Una introducción visual al lenguaje algebraico.", true),
                    new("item-2", "Construye una expresión", "Práctica", "Representa situaciones cotidianas con expresiones.", true)
                ], 100)
            ]),
            new("section-2", "Unidad 2", "Ecuaciones lineales",
            [
                new("lesson-2", "Igualdades y equivalencias", "Comprende el equilibrio de una ecuación.",
                [
                    new("item-3", "La balanza algebraica", "Video", "Observa cómo conservar una igualdad.", true),
                    new("item-4", "Resuelve paso a paso", "Práctica", "Aplica operaciones inversas.")
                ], 50)
            ]),
            new("section-3", "Unidad 3", "Aplicaciones y reto final",
            [
                new("lesson-3", "Modelación y evaluación", "Usa ecuaciones y completa la actividad final.",
                [
                    new("item-5", "Problemas de contexto", "Taller", "Modela situaciones mediante una ecuación."),
                    new("item-6", "Quiz: Conociendo México", "Quiz", "Cinco preguntas generales para cerrar el curso.")
                ])
            ])
        ],
        62);

    public static IReadOnlyList<QuizQuestion> MexicoQuiz { get; } =
    [
        Question("q1", "¿Cuál es la capital de México?", "Ciudad de México", "Guadalajara", "Monterrey", "Puebla"),
        Question("q2", "¿Qué colores tiene la bandera mexicana?", "Verde, blanco y rojo", "Azul, blanco y rojo", "Verde y amarillo", "Rojo y negro"),
        Question("q3", "¿En qué península se encuentra Cancún?", "Yucatán", "Baja California", "Florida", "Osa"),
        Question("q4", "¿Qué civilización construyó Chichén Itzá?", "Maya", "Inca", "Romana", "Egipcia"),
        Question("q5", "¿Cuál es la moneda oficial de México?", "Peso mexicano", "Dólar", "Quetzal", "Sol")
    ];

    public static IReadOnlyList<StudentProgress> Students { get; } =
    [
        new("s1", "Ethan Martínez", "EM", "Respondiendo", 4, 5),
        new("s2", "Sofía Torres", "ST", "Finalizado", 5, 5, 80),
        new("s3", "Lucas Herrera", "LH", "Respondiendo", 2, 5),
        new("s4", "Valentina Ruiz", "VR", "En espera", 0, 5)
    ];

    private static QuizQuestion Question(string id, string text, string correct, params string[] distractors)
    {
        var options = new[] { correct }.Concat(distractors)
            .Select((value, index) => new QuizOption($"{id}-{index + 1}", value)).ToArray();
        return new QuizQuestion(id, text, options, options[0].Id);
    }
}

