from protowhat.Feedback import Feedback, FeedbackComponent


def test_feedback_get_message():
    # Given
    conclusion = FeedbackComponent(message="    This is not good.   ")
    fc1 = FeedbackComponent("This is worse.    ")
    fc2 = FeedbackComponent("    This is even worse.")
    content_components = [fc1, fc2]
    feedback = Feedback(conclusion, content_components)

    # When
    message = feedback.get_message()

    # Then
    assert message == "This is worse. This is even worse. This is not good."
