*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${HOME}    xpath=//ion-fab-button
${NOTIFICATIONS_OUTLINE}    id=notifications-button
${BTN_CUSTOMERSIGNUP}    id=btn_CustomerSignup
${BTN_CLEANSURVEY}    id=btn_CleanSurvey
${BTN_SITESURVEY}    id=btn_SiteSurvey

*** Keywords ***
Verify Home Page Loaded
    [Documentation]    Verifies that the Home page main controls are visible and ready.
    Wait For Element To Be Ready    ${HOME}
    Wait For Element To Be Ready    ${NOTIFICATIONS_OUTLINE}
    Wait For Element To Be Ready    ${BTN_CUSTOMERSIGNUP}
    Wait For Element To Be Ready    ${BTN_CLEANSURVEY}
    Wait For Element To Be Ready    ${BTN_SITESURVEY}

Click Home
    [Documentation]    Clicks the Home floating button.
    Click When Ready    ${HOME}

Click Notifications Outline
    [Documentation]    Clicks the notifications icon on the Home page.
    Click When Ready    ${NOTIFICATIONS_OUTLINE}

Click Customer Signup
    [Documentation]    Clicks the Customer Signup button.
    Click When Ready    ${BTN_CUSTOMERSIGNUP}

Click Clean Survey
    [Documentation]    Clicks the Clean Survey button.
    Click When Ready    ${BTN_CLEANSURVEY}

Click Site Survey
    [Documentation]    Clicks the Site Survey button.
    Click When Ready    ${BTN_SITESURVEY}
