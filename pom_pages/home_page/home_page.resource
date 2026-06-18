*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${HOME_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home'] or normalize-space(.)='home']
${NOTIFICATIONS_BUTTON}    id=notifications-button
${CUSTOMER_SIGNUP_BUTTON}    id=btn_CustomerSignup
${CLEAN_SURVEY_BUTTON}    id=btn_CleanSurvey
${SITE_SURVEY_BUTTON}    id=btn_SiteSurvey

*** Keywords ***
Verify Home Page Loaded
    [Documentation]    Verifies that key Home page controls are visible and ready.
    Wait For Element To Be Ready    ${HOME_BUTTON}
    Wait For Element To Be Ready    ${NOTIFICATIONS_BUTTON}
    Wait For Element To Be Ready    ${CUSTOMER_SIGNUP_BUTTON}
    Wait For Element To Be Ready    ${CLEAN_SURVEY_BUTTON}
    Wait For Element To Be Ready    ${SITE_SURVEY_BUTTON}

Verify Home Button Visible
    [Documentation]    Verifies that the Home button is visible.
    Wait For Element To Be Ready    ${HOME_BUTTON}

Verify Notifications Button Visible
    [Documentation]    Verifies that the notifications button is visible.
    Wait For Element To Be Ready    ${NOTIFICATIONS_BUTTON}

Click Home Button
    [Documentation]    Clicks the Home floating action button.
    Click When Ready    ${HOME_BUTTON}

Click Notifications Button
    [Documentation]    Clicks the notifications button on the Home page.
    Click When Ready    ${NOTIFICATIONS_BUTTON}

Click Customer Signup Button
    [Documentation]    Clicks the Customer Signup button.
    Click When Ready    ${CUSTOMER_SIGNUP_BUTTON}

Click Clean Survey Button
    [Documentation]    Clicks the Clean Survey button.
    Click When Ready    ${CLEAN_SURVEY_BUTTON}

Click Site Survey Button
    [Documentation]    Clicks the Site Survey button.
    Click When Ready    ${SITE_SURVEY_BUTTON}
