// pages/enteredText.tsx
import dynamic from 'next/dynamic';
import { useRouter } from 'next/router';

const RenderPdf = dynamic(() => import('../app/components/render_pdf'), {
  ssr: false,
});

const PdfContent = () => {
  const router = useRouter();
  const { url } = router.query;
  return (
    <>
    <RenderPdf text={url}/>
    </>
  );
};

export default PdfContent;

