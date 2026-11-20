import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="container">
      <div className="page-title"><h1 style={{ fontSize: 'clamp(2rem,4vw,2.8rem)' }}>About and methodology</h1><p>What the model is, how it was built and, just as important, what it cannot do.</p></div>
      <div className="prose" style={{ paddingBottom: 40 }}>
        <h2>Objective</h2>
        <p>CreditWise AI predicts whether a loan applicant is likely to have <strong>recorded payment difficulty</strong>, using information available on the application. It is a machine-learning project that shows the full path from data to an explained prediction.</p>
        <h2>Dataset and target</h2>
        <p>The model is trained on the public <strong>Home Credit Default Risk</strong> dataset. The target is 1 for recorded payment difficulty and 0 for no recorded payment difficulty. It is <strong>not</strong> trained on CIBIL&apos;s proprietary data, and the output is not a CIBIL or any other official credit score.</p>
        <h2>Preprocessing</h2>
        <ul>
          <li>125 input features: 109 numeric and 16 categorical.</li>
          <li>Numeric columns: median imputation, then standard scaling.</li>
          <li>Categorical columns: most-frequent imputation, then one-hot encoding, giving 247 model columns.</li>
          <li>Derived features (age and employment in years, credit-to-income, instalment-to-income, goods-to-credit) are calculated for you when their inputs are present.</li>
        </ul>
        <div className="callout"><strong>Partial inputs.</strong> Any field you leave blank is filled by the saved imputers with a typical training value. That is not recovered information: the result is simply less specific to the applicant, and the completeness indicator tells you how much of the model&apos;s key information you supplied.</div>
        <h2>Models, tuning and selection</h2>
        <p>Six models were compared: Gradient Boosting, SVM, Logistic Regression, Random Forest, Bagging and Decision Tree. Three were tuned with cross-validated search on PR-AUC, which suits a rare positive class. Gradient Boosting led on ROC-AUC, PR-AUC, recall and F1 and was selected. Details are on the <Link to="/analytics#comparison">Analytics</Link> page.</p>
        <h2>Threshold optimisation</h2>
        <p>Scores at or above the saved threshold of 0.15 are classed as recorded payment difficulty. The threshold was chosen from a sweep of precision, recall and F1 rather than using the default 0.5. The curve is on the <Link to="/analytics#threshold">Analytics</Link> page.</p>
        <h2>Explainability</h2>
        <p>Global importance comes from SHAP values computed during the original analysis. For each prediction made here, exact tree SHAP values are computed on the saved model, grouped by original input, and checked to add up to the model output. Fields you did not provide are labelled as assumed because they still influence the score.</p>
        <h2>Limitations</h2>
        <ul>
          <li>Precision is about 25% at the saved threshold: most flagged applicants in the test data did not have recorded difficulty. Treat the output as a rough signal.</li>
          <li>The score has not been calibrated, so it should not be read as a guaranteed real-world probability.</li>
          <li>The dataset is historical and from one lender; results may not transfer to other populations or time periods.</li>
          <li>The model uses personal attributes such as gender and education. Fairness and bias were not assessed in the exported work, and it must not be used for real lending decisions.</li>
          <li>Predictions based on few details can be much less reliable.</li>
          <li>The model is not certified or approved for loan approval or any regulated use.</li>
        </ul>
        <h2>Privacy</h2>
        <p>Each prediction is a stateless request. Applicant details are not stored in a database or logged, and results live only in your browser tab&apos;s memory.</p>
      </div>
    </div>
  )
}
