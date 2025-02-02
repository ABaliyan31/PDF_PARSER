import { useState } from "react";
import { useRouter } from "next/router";

const InputForm = () => {
  const [url, setUrl] = useState("");  // State to hold the URL input
  const router = useRouter();  // Next.js router to navigate

  const handleSubmit = () => {
    // Navigate to /entered_text with the entered URL as a query parameter
    router.push({
      pathname: "/pdf_content",
      query: { url: url },  // Passing the URL as a query parameter
    }
    );
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-black">
      <div className="p-6 rounded-lg shadow-lg">
        <h1 className="text-4xl font-semibold text-white mb-4 text-center">
          PDF Transcriber
        </h1>
        <div className="flex flex-col sm:flex-row gap-4">
          <input
            type="text"
            placeholder="Enter a valid pdf url to transcribe"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-[800px] px-2 py-2 rounded-md border-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-500 bg-gray-800"
          />
          <button
            onClick={handleSubmit}
            disabled={!url}
            className={`px-6 py-2 rounded-md focus:outline-none focus:ring-2 transition duration-200 
          ${url
                ? "bg-blue-500 text-white hover:bg-blue-600 focus:ring-blue-300 cursor-pointer"
                : "bg-gray-600 text-gray-400 cursor-not-allowed"
              }`}
          >
            Submit
          </button>
        </div>
        <h1 className="text-xl text-white mt-8 text-center">
        I would like to die on Mars. Just not on impact.
        </h1>
      </div>
    </div>

  );
};

export default InputForm;
