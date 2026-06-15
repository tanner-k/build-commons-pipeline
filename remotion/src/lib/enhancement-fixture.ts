import samplePlan from '../../../schemas/fixtures/sample_enhancement_plan.json';
import {enhancementPlanSchema} from '../types/enhancement';

export const SAMPLE_PLAN = enhancementPlanSchema.parse(samplePlan);
