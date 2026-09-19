import { MAX_QUESTION_LENGTH } from "../constants.js";

function ChatInput({ value, onChange, onSubmit, isLoading }) {
  const trimmed = value.trim();
  const isDisabled = isLoading || trimmed.length === 0 || value.length > MAX_QUESTION_LENGTH;

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isDisabled) {
        onSubmit();
      }
    }
  }

  return (
    <form
      className="chat-input-shell"
      onSubmit={(event) => {
        event.preventDefault();
        if (!isDisabled) {
          onSubmit();
        }
      }}
    >
      <label htmlFor="question-input">Ask a question</label>
      <div className="chat-input-row">
        <textarea
          id="question-input"
          value={value}
          onChange={(event) => onChange(event.target.value.slice(0, MAX_QUESTION_LENGTH))}
          onKeyDown={handleKeyDown}
          placeholder="Ask about Computer Engineering courses, skills, careers, AI, internships..."
          maxLength={MAX_QUESTION_LENGTH}
          rows={3}
          disabled={isLoading}
        />
        <button type="submit" disabled={isDisabled}>
          Send
        </button>
      </div>
      <div className="input-footer">
        <span>Enter sends, Shift+Enter adds a new line.</span>
        <span className={value.length >= MAX_QUESTION_LENGTH ? "limit-warning" : ""}>
          {value.length}/{MAX_QUESTION_LENGTH}
        </span>
      </div>
    </form>
  );
}

export default ChatInput;
