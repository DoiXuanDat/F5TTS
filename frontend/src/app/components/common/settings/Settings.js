import React from "react";

const Settings = ({ noTextTime, setNoTextTime, sentencePause, setSentencePause, paragraphPause, setParagraphPause, splitBy, setSplitBy, dllitems, setDllitems, splitSentences, deleteSpecialCharacter }) => {
  return (
    <div className="settings">
      <div>
        <p>- Thời gian ảnh/video không có text: </p>
        <input
          type="number"
          value={noTextTime}
          onChange={(e) => setNoTextTime(e.target.value)}
        />{" "}
        (s)
      </div>
      <div>
        <p>- Thời gian nghỉ giữa các câu:</p>
        <input
          type="number"
          value={sentencePause}
          onChange={(e) => setSentencePause(e.target.value)}
        />{" "}
        (s)
      </div>
      <div>
        <p>- Thời gian nghỉ giữa các đoạn: </p>
        <input
          type="number"
          value={paragraphPause}
          onChange={(e) => setParagraphPause(e.target.value)}
        />{" "}
        (s)
      </div>
      <div>
        <p>- Chia câu theo dấu: </p>
        <input
          className="me-2"
          type="text"
          value={splitBy}
          onChange={(e) => setSplitBy(e.target.value)}
        />
        <button className="me-5 bg-primary" onClick={splitSentences}>Chia</button>
        <p>Xóa kí tự: </p>
        <input
          className="me-2"
          type="text"
          value={dllitems}
          onChange={(e) => setDllitems(e.target.value)}
        />
        <button className="bg-danger" onClick={deleteSpecialCharacter}>Xóa</button>
      </div>
    </div>
  );
};

export default Settings;
