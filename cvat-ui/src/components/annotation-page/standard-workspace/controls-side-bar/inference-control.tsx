// cvat-ui/src/components/annotation-page/standard-workspace/controls-side-bar/inference-control.tsx

import React from 'react';
import { Button, notification } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';
import { Canvas } from 'cvat-canvas-wrapper';
import CVATTooltip from 'components/common/cvat-tooltip';

interface Props {
    canvasInstance: Canvas;
}

async function triggerInference(image: Blob, scale: number) {
    const formData = new FormData();
    formData.append('image', new File([image], 'current-image.png', { type: 'image/png' }));
    formData.append('scale', scale.toString());

    try {
        const response = await fetch('http://localhost:8000/infer', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Failed to process the X-ray');
        }

        const data = await response.json();
        console.log('Inference Response:', data);
        notification.success({
            message: 'Inference Successful',
            description: data.Message,
        });
    } catch (error) {
        console.error('Error:', error);
        notification.error({
            message: 'Inference Failed',
            description: error.message,
        });
    }
}

function InferenceControl(props: Props): JSX.Element {
    const { canvasInstance } = props;

    const handleClick = async (): Promise<void> => {
        try {
            // Assuming canvasInstance has a method to get the current image as a Blob
            const imageBlob = await canvasInstance.getCurrentImage(); // Hypothetical method
            const scale = 1.0; // Example scale value

            triggerInference(imageBlob, scale);
        } catch (error) {
            console.error('Error fetching the current image:', error);
            notification.error({
                message: 'Error',
                description: 'Failed to retrieve the current image from the canvas.',
            });
        }
    };

    return (
        <CVATTooltip title='Run Inference' placement='right'>
            <Button
                onClick={handleClick}
                className='cvat-inference-control'
                icon={<ExperimentOutlined />}
            >
                Inference
            </Button>
        </CVATTooltip>
    );
}

export default React.memo(InferenceControl);
