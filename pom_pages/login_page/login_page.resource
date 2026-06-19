*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${HOME_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home'] or normalize-space(.)='home']
${ARROW_BACK_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='arrow back'] or normalize-space(.)='arrow back']
${PASSWORD_TEXTBOX}    xpath=//input[@name='ion-input-1']
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space(.)='SIGN IN']

*** Keywords ***
Click Home Button
    Click When Ready    ${HOME_BUTTON}

Click Arrow Back Button
    Click When Ready    ${ARROW_BACK_BUTTON}

Enter Password
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Input Password    ${PASSWORD_TEXTBOX}    ${password}

Click Sign In Button
    Click When Ready    ${SIGN_IN_BUTTON}
