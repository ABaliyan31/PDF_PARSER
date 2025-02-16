import { useCallback, useState, useEffect, useRef } from 'react';
import { useResizeObserver } from '@wojtekmaj/react-hooks';
import { pdfjs, Document, Page } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

import type { PDFDocumentProxy } from 'pdfjs-dist';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString();

const options = {
    cMapUrl: '/cmaps/',
    standardFontDataUrl: '/standard_fonts/',
};

const resizeObserverOptions = {};

const maxWidth = 800;

function highlightPattern(text, pattern) {
    return text.replace(pattern, (value) => `<mark>${value}</mark>`);
  }

export default function Sample({ text }) {
    const [numPages, setNumPages] = useState<number>();
    const [containerRef, setContainerRef] = useState<HTMLElement | null>(null);
    const [publicUrl, setPublicUrl] = useState('');
    const [containerWidth, setContainerWidth] = useState<number>();
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [extractedText, setExtractedText] = useState<any>(undefined); // Holds both text and bounding boxes
    const [currentPageText, setCurrentPageText] = useState<any>([]); // Holds the text and bbox for the current page
    const [loading, setLoading] = useState<boolean>(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [currentMatchIndex, setCurrentMatchIndex] = useState<number>(-1);
    const [textScale, setScale] = useState(1);
    const matchesRef = useRef<Array<HTMLSpanElement>>([]);
    const [zoom, setZoom] = useState(0.9);
    const [error, setError] = useState(false);
    const textContainerRef = useRef(null);

    const onResize = useCallback<ResizeObserverCallback>((entries) => {
        const [entry] = entries;

        if (entry) {
            setContainerWidth(entry.contentRect.width);
        }
    }, []);

    const textRenderer = useCallback(
        (textItem) => highlightPattern(textItem.str, searchTerm),
        [searchTerm]
    );

    const zoomIn = () => {
        setZoom((prevZoom) => prevZoom * 1.1);
    };

    const zoomOut = () => {
        setZoom((prevZoom) => prevZoom / 1.1);
    };

    useResizeObserver(containerRef, resizeObserverOptions, onResize);

    function onDocumentLoadSuccess({ numPages: nextNumPages }: PDFDocumentProxy): void {
        setNumPages(nextNumPages);
    }

    const handleTextSelection = () => {
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        setSearchTerm(selectedText);
    };

    const fetchExtractedText = async () => {
        try {
            const response = await fetch('http://localhost:8000/extract_text_from_pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ pdf_url: text }),
            });

            if (!response.ok) {
                throw new Error('Failed to fetch extracted text');
            }

            const data = await response.json();
            setExtractedText(data?.extracted_text); // Set the text along with bounding boxes
            setCurrentPageText(data?.extracted_text[1]); // Set current page text and bounding boxes
            setPublicUrl(data.file_url);
        } catch (error) {
            setError(true);
            setCurrentPageText([{ text: 'Error fetching extracted text.', bbox: [0, 0, 0, 0] }]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (text) {
            fetchExtractedText();
        }

        const textContainer = textContainerRef.current;
        if (textContainer) {
            textContainer.addEventListener('mouseup', handleTextSelection);
        } else {
            console.log("textContainer is not available");
        }

        return () => {
            if (textContainer) {
                textContainer.removeEventListener('mouseup', handleTextSelection);
            }
        };
    }, [text, loading]);

    useEffect(() => {
        if (extractedText && currentPage && extractedText[currentPage]) {
            setCurrentPageText(extractedText[currentPage]);
        }
    }, [currentPage, extractedText]);

    const highlightText = (text, search) => {
        if (!search) return text;
        const escapeRegExp = (string) => string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const regex = new RegExp(`(${escapeRegExp(search)})`, "gi");
        const parts = text.split(regex);
        return parts.map((part, index) =>
            part.toLowerCase() === search.toLowerCase() ? (
                <span
                    key={index}
                    className="bg-yellow-400 text-black px-1"
                    ref={(el) => el && matchesRef.current.push(el)}
                >
                    {part}
                </span>
            ) : (
                part
            )
        );
    };

    const renderTextWithBoundingBoxes = (textItems, scale = textScale) => {
        return textItems.map((item, index) => {
            const [x0, y0, x1, y1] = item.bbox;

            const style = {
                position: 'absolute',
                left: `${(x0 * scale)*1.1}px`,
                top: `${(y0 * scale)*1.1}px`,
                width: `${((x1 - x0) * scale)*1.1}px`,
                height: `${((y1 - y0) * scale)*1.1}px`,
                backgroundColor: 'rgba(50, 50, 50, 0.2)',
                padding: '2px',
                color: 'black',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'visible', 
                fontSize: `${7 * scale}px`,
                lineHeight: 1,
                whiteSpace: 'nowrap'
            };
            return (
                <span
                    key={index}
                    style={style}
                    className="absolute"
                >
                    {highlightText(item.text, searchTerm)}
                </span>
            );
        });
    };


    return (
        <>
            {loading && (
                <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
                    <div className="p-6 bg-gray-900 text-white rounded-lg shadow-lg flex flex-col items-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-t-4 border-blue-500"></div>
                        <p className="mt-4 text-lg font-semibold">Loading...</p>
                    </div>
                </div>
            )}
            {error && (
                <div className="fixed inset-0 flex justify-center items-center">
                    <h3 className="text-gray-500 font-bold">Error while fetching PDF</h3>
                </div>
            )}
            {(!loading && !error) && (
                <div className="flex justify-start items-start h-screen w-screen bg-black p-4 mt-8 fixed overflow-hidden">
                    <div className="mx-auto flex justify-center w-full space-x-2">
                        <div className="w-full p-4 rounded-lg shadow-lg bg-white max-h-[890px] overflow-auto relative">
                            {publicUrl && (
                                <Document
                                    file={publicUrl}
                                    onLoadSuccess={onDocumentLoadSuccess}
                                    options={options}
                                >
                                    <Page
                                        key={`page_${currentPage}`}
                                        pageNumber={currentPage}
                                        width={containerWidth ? Math.min(containerWidth, maxWidth) : maxWidth}
                                        scale={zoom}
                                        customTextRenderer={textRenderer}
                                    />
                                </Document>
                            )}
                            {/* <div className="relative" style={{ position: 'relative' }}>
                                {renderTextWithBoundingBoxes(currentPageText)}
                            </div> */}
                        </div>


                        <div className="w-full p-4 rounded-lg shadow-lg bg-white max-h-[890px] overflow-auto" ref={textContainerRef}>
                            <h3 className="text-white text-lg font-semibold mb-4">Extracted Text</h3>
                            <pre className="text-white text-sm whitespace-pre-wrap font-mono">
                            <div className="relative" style={{ position: 'relative' }}>
                                {renderTextWithBoundingBoxes(currentPageText)}
                            </div> 
                            </pre>
                        </div>
                    </div>

                    <div className="w-full bg-black fixed top-0 left-0 right-0 z-10">
                        <div className="flex justify-center items-center">
                            <div className="w-full max-w-2xl px-4 py-2 flex justify-between items-center bg-black rounded-lg shadow-md gap-4">
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={zoomIn}
                                        className="w-7 h-7 bg-transparent border-2 border-blue-500 text-blue-500 rounded-full flex items-center justify-center text-lg hover:bg-blue-500 hover:text-white transition duration-200"
                                    >
                                        +
                                    </button>
                                    <span className="text-white ml-5">magnify</span>
                                    <button
                                        onClick={zoomOut}
                                        className="w-7 h-7 bg-transparent border-2 border-blue-500 text-blue-500 rounded-full flex items-center justify-center text-lg hover:bg-blue-500 hover:text-white transition duration-200"
                                    >
                                        -
                                    </button>
                                </div>
                                <input
                                    type="text"
                                    placeholder="Search text..."
                                    onChange={(e) => {
                                        setSearchTerm(e.target.value);
                                        setCurrentMatchIndex(-1);
                                    }}
                                    className="w-[400px] px-2 py-2 rounded-md border-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-gray-500 bg-gray-800"
                                />
                                <div className="flex space-x-4 ml-4 items-center">
                                    <input
                                        type="number"
                                        defaultValue={1}
                                        onChange={(e) => {
                                            let pageNum = e.target.value === undefined ? undefined : parseInt(e.target.value, 10);
                                            if (pageNum === undefined || (pageNum > 0 && pageNum <= numPages)) {
                                                setCurrentPage(pageNum);
                                                setSearchTerm(prev => prev);
                                            }
                                        }}
                                        className="w-20 h-10 text-center text-lg bg-black text-white border border-gray-500 rounded-md p-2"
                                        min="1"
                                        max={numPages}
                                    />
                                    <span>{`/${numPages}`}</span>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <button
                                        onClick={()=> setScale((prev)=> prev*1.1)}
                                        className="w-7 h-7 bg-transparent border-2 border-blue-500 text-blue-500 rounded-full flex items-center justify-center text-lg hover:bg-blue-500 hover:text-white transition duration-200"
                                    >
                                        +
                                    </button>
                                    <span className="text-white ml-5">magnify</span>
                                    <button
                                        onClick={()=> setScale((prev)=> prev*0.9)}
                                        className="w-7 h-7 bg-transparent border-2 border-blue-500 text-blue-500 rounded-full flex items-center justify-center text-lg hover:bg-blue-500 hover:text-white transition duration-200"
                                    >
                                        -
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
